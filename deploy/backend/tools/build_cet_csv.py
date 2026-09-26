"""一次性数据预处理脚本：从 ECDICT 提取「四级 / 六级」词汇，生成知岸 seed_words 格式 CSV。

用法（纯本地运行，不部署到服务器）：
    python backend/tools/build_cet_csv.py

前置：
- backend/tools/ecdict.csv 需已存在（由 build_kaoyan_csv.py 下载，约 65 MB）。

流程：
1. 单遍扫描 ecdict.csv，分别按 cet4 / cet6 标签筛选；
2. 清洗（只要单个英文单词、小写、去重）并映射字段（复用考研脚本同一套逻辑）；
3. 输出 backend/cet4_words.csv 与 backend/cet6_words.csv（UTF-8 BOM + CRLF，
   表头与 seed_words.csv 一致）；
4. 打印统计与示例。

tags 说明：
- ECDICT 源标签为 "cet4" / "cet6"；
- 输出 tags 写知岸内部中文标签「四级」「六级」，与 seed_words.csv 的「考研」保持一致，
  使后端 words.py 的 BOOKS（tag=四级/六级）能 LIKE 匹配到。
- 同一单词若同时含 cet4 与 cet6 标签，会分别写入两个 CSV；seed.py 导入时会把
  tags 并集合并为「四级,六级」。
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

# 控制台统一 UTF-8，避免 Windows GBK 编码下中文/国际音标打印报错
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------- 常量 ----------

BASE_DIR = Path(__file__).resolve().parent           # backend/tools
ECDICT_CSV = BASE_DIR / "ecdict.csv"
OUT_DIR = BASE_DIR.parent                            # backend/

# ECDICT 源标签 → 输出文件名
BOOK_FILES = {
    "cet4": OUT_DIR / "cet4_words.csv",
    "cet6": OUT_DIR / "cet6_words.csv",
}

# ECDICT 源标签 → 知岸内部 tags（与 seed_words.csv 的「考研」一致）
BOOK_TAGS = {
    "cet4": "四级",
    "cet6": "六级",
}

# 与 seed_words.csv 一致的表头
HEADER = ["word", "phonetic", "pos", "meaning", "example_en", "example_zh", "tags", "difficulty"]

# ECDICT translation 行首词性缩写 → 知岸词性
POS_FORM_MAP = {
    "n": "n.",
    "a": "adj.",
    "adj": "adj.",
    "v": "v.",
    "vt": "v.",
    "vi": "v.",
    "adv": "adv.",
    "prep": "prep.",
    "conj": "conj.",
    "pron": "pron.",
    "num": "num.",
    "art": "art.",
    "int": "int.",
    "interj": "int.",
    "pl": "n.",
    "aux": "v.",
}

# 构词法标记（前缀/后缀/缩写等），剥离但不计入词性
NON_POS_MARKERS = {"pref", "suf", "abbr"}

# 只接受单个英文单词（小写字母组成）
WORD_RE = re.compile(r"[a-z]+")

# translation 行首词性前缀："n." / "vt." / "a." 等
POS_PREFIX_RE = re.compile(r"^([a-z]+)\.\s*(.*)$")

# 统计：translation 行首词性里没有映射到的
unmapped_pos: Counter = Counter()


# ---------- 字段映射（与 build_kaoyan_csv.py 一致） ----------


def _int(v: object) -> int | None:
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def clean_word(w: object) -> str | None:
    s = (w or "").strip().lower()
    return s if WORD_RE.fullmatch(s) else None


def extract_pos_meaning(translation: str) -> tuple[str, str]:
    pos_forms: list[str] = []
    meanings: list[str] = []
    for raw_line in (translation or "").replace("\\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[网络]"):
            continue

        m = POS_PREFIX_RE.match(line)
        if m:
            abbrev = m.group(1).lower()
            form = POS_FORM_MAP.get(abbrev)
            content = m.group(2).strip()
            if form is not None:
                if form not in pos_forms:
                    pos_forms.append(form)
            elif abbrev in NON_POS_MARKERS:
                pass
            else:
                unmapped_pos[abbrev] += 1
                content = f"{abbrev}. {content}".strip()
        else:
            content = line

        content = re.sub(r"^\[[^\]]+\]\s*", "", content).strip()
        if content:
            meanings.append(content)

    return "/".join(pos_forms), "；".join(meanings)


def difficulty_of(collins_raw: object, bnc_raw: object, frq_raw: object) -> int:
    collins = _int(collins_raw)
    bnc = _int(bnc_raw)
    frq = _int(frq_raw)
    if (collins is not None and collins >= 4) or (bnc is not None and bnc <= 5000):
        return 1
    if (collins == 3) or (bnc is not None and bnc <= 30000) or (frq is not None and frq <= 30000):
        return 2
    return 3


# ---------- 筛选 ----------


def build() -> tuple[dict[str, dict[str, dict]], Counter]:
    """单遍扫描：按 cet4 / cet6 标签筛选，清洗、去重。返回 {key: {word: row}}。"""
    kept: dict[str, dict[str, dict]] = {key: {} for key in BOOK_FILES}
    stat: Counter = Counter()
    with ECDICT_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            raw_tags = (row.get("tag") or "").split()
            for key in BOOK_FILES:
                if key not in raw_tags:
                    continue
                stat[f"{key}_matched"] += 1
                word = clean_word(row.get("word"))
                if word is None:
                    stat[f"{key}_excluded_invalid"] += 1
                    continue
                if word in kept[key]:
                    stat[f"{key}_dedup"] += 1
                    continue
                kept[key][word] = row
    for key in BOOK_FILES:
        stat[f"{key}_kept"] = len(kept[key])
    return kept, stat


def to_rows(kept: dict[str, dict], tags_value: str) -> tuple[list[list], int, int]:
    rows: list[list] = []
    phonetic_missing = 0
    meaning_missing = 0
    for word in sorted(kept):
        r = kept[word]
        phonetic = (r.get("phonetic") or "").strip()
        phonetic = phonetic.replace("ә", "ə")
        pos, meaning = extract_pos_meaning(r.get("translation") or "")
        if not phonetic:
            phonetic_missing += 1
        if not meaning:
            meaning_missing += 1
        difficulty = difficulty_of(r.get("collins"), r.get("bnc"), r.get("frq"))
        rows.append([word, phonetic, pos, meaning, "", "", tags_value, difficulty])
    return rows, phonetic_missing, meaning_missing


def write_output(path: Path, rows: list[list]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write("﻿")  # BOM
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(HEADER)
        w.writerows(rows)


# ---------- 主流程 ----------


def main() -> None:
    if not ECDICT_CSV.exists():
        print(f"[错误] 未找到 {ECDICT_CSV}，请先运行 build_kaoyan_csv.py 下载。")
        sys.exit(1)

    kept, stat = build()

    for key, path in BOOK_FILES.items():
        tags_value = BOOK_TAGS[key]
        rows, phonetic_missing, meaning_missing = to_rows(kept[key], tags_value)
        write_output(path, rows)

        print(f"\n===== {key}（tags={tags_value}） =====")
        print(f"  tag 命中原始词条     : {stat.get(f'{key}_matched', 0)}")
        print(f"  排除（非单词）       : {stat.get(f'{key}_excluded_invalid', 0)}")
        print(f"  去重（同一词多条）   : {stat.get(f'{key}_dedup', 0)}")
        print(f"  最终保留单词数       : {stat.get(f'{key}_kept', 0)}")

        diff_counter = Counter(r[7] for r in rows)
        print(f"  difficulty 分布      : 1={diff_counter.get(1, 0)}, 2={diff_counter.get(2, 0)}, 3={diff_counter.get(3, 0)}")
        print(f"  音标缺失 / 释义缺失 : {phonetic_missing} / {meaning_missing}")
        print(f"  输出文件             : {path}（{path.stat().st_size / 1024:.1f} KB）")

    # 重叠统计：同时含 cet4 与 cet6 的词
    overlap = sorted(set(kept["cet4"]) & set(kept["cet6"]))
    print(f"\n===== 四级 ∩ 六级 重叠词数 =====\n  {len(overlap)}")

    if unmapped_pos:
        print("\n===== 未映射的 translation 词性前缀（需核对 POS_FORM_MAP） =====")
        for letter, count in unmapped_pos.most_common():
            print(f"  {letter!r}: {count}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
