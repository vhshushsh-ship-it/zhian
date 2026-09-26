"""一次性数据预处理脚本：从 ECDICT 提取「考研英语」词汇，生成知岸 seed_words 格式 CSV。

用法（纯本地运行，不部署到服务器）：
    python backend/tools/build_kaoyan_csv.py

流程：
1. 下载 ecdict.csv（不存在时），保存到 backend/tools/ecdict.csv；
2. 第一遍扫描：打印 tag 列所有唯一值 + 出现次数，供确认「考研」真实标签；
3. 第二遍扫描：按 KAOYAN_TAG 筛选，清洗（只要单个英文单词、小写、去重）并映射字段；
4. 输出 backend/seed_words_kaoyan.csv（UTF-8 BOM + CRLF，表头与 seed_words.csv 一致）；
5. 打印统计与示例。

实测说明（基于 skywind3000/ECDICT master 的 ecdict.csv）：
- 考研词在 tag 列的标签为 "ky"（共 4801 条），另有 gre/toefl/cet6/ielts/cet4/gk/zk 等；
- pos 列为空：词性以行首前缀内嵌在 translation 字段（如 "n. ..." / "vt. ..." / "a. ..."），
  其中 "a." = 形容词、"vt./vi./v." = 动词、"pl." = 复数名词、"aux." = 助动词；
- translation 末尾常有 "[网络]" 网络释义段，属低质量内容，直接丢弃；
- definition 列为英文释义，本脚本不采用（例句按需求留空）。

注意：ecdict.csv 约几十 MB、76 万词条，不要 git add（已加入 .gitignore）。
"""

import csv
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

# 控制台统一 UTF-8，避免 Windows GBK 编码下中文/国际音标打印报错
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------- 常量 ----------

ECDICT_URL = "https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv"

BASE_DIR = Path(__file__).resolve().parent           # backend/tools
ECDICT_CSV = BASE_DIR / "ecdict.csv"
OUT_CSV = BASE_DIR.parent / "seed_words_kaoyan.csv"  # backend/seed_words_kaoyan.csv

# 与 seed_words.csv 一致的表头
HEADER = ["word", "phonetic", "pos", "meaning", "example_en", "example_zh", "tags", "difficulty"]

# 考研词在 ECDICT tag 列的真实标签（实测为 "ky"，运行后先核对第一步打印的 tag 分布）
KAOYAN_TAG = "ky"

# ECDICT translation 行首词性缩写 → 知岸词性（n./v./adj./adv./prep./pron./conj./num./art./int.）
POS_FORM_MAP = {
    "n": "n.",       # 名词
    "a": "adj.",     # 形容词（ECDICT 用 "a."，非 "adj."）
    "adj": "adj.",
    "v": "v.",       # 动词
    "vt": "v.",      # 及物动词
    "vi": "v.",      # 不及物动词
    "adv": "adv.",   # 副词
    "prep": "prep.", # 介词
    "conj": "conj.", # 连词
    "pron": "pron.", # 代词
    "num": "num.",   # 数词
    "art": "art.",   # 冠词
    "int": "int.",   # 感叹词
    "interj": "int.",# 感叹词（拼写完整形式）
    "pl": "n.",      # 复数名词 → 名词
    "aux": "v.",     # 助动词 → 动词
}

# 构词法标记（前缀/后缀/缩写等），剥离但不计入词性
NON_POS_MARKERS = {"pref", "suf", "abbr"}

# 只接受单个英文单词（小写字母组成，无空格/连字符/撇号/数字/符号）
WORD_RE = re.compile(r"[a-z]+")

# translation 行首词性前缀："n." / "vt." / "a." 等
POS_PREFIX_RE = re.compile(r"^([a-z]+)\.\s*(.*)$")

# 统计：translation 行首词性里没有映射到的（用于核对 POS_FORM_MAP 是否覆盖）
unmapped_pos: Counter = Counter()


# ---------- 下载 ----------


def download() -> None:
    """下载 ecdict.csv，已存在则跳过。"""
    if ECDICT_CSV.exists():
        print(f"[下载] 已存在，跳过：{ECDICT_CSV.name}（{ECDICT_CSV.stat().st_size / 1024 / 1024:.1f} MB）")
        return
    print(f"[下载] {ECDICT_URL}\n        -> {ECDICT_CSV}")
    tmp = ECDICT_CSV.with_suffix(".csv.part")
    try:
        urllib.request.urlretrieve(ECDICT_URL, tmp)
        tmp.rename(ECDICT_CSV)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    print(f"[下载] 完成，{ECDICT_CSV.stat().st_size / 1024 / 1024:.1f} MB")


# ---------- 第一遍扫描 ----------


def scan() -> Counter:
    """统计 tag 列所有唯一标签 + 出现次数。"""
    tag_counter: Counter = Counter()
    with ECDICT_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            for t in (row.get("tag") or "").split():
                tag_counter[t] += 1
    return tag_counter


# ---------- 字段映射 ----------


def _int(v: object) -> int | None:
    """把空串/0 视为无值，其余转 int。"""
    try:
        n = int(str(v).strip())
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def clean_word(w: object) -> str | None:
    """只保留单个英文单词：小写、纯字母。否则返回 None。"""
    s = (w or "").strip().lower()
    return s if WORD_RE.fullmatch(s) else None


def extract_pos_meaning(translation: str) -> tuple[str, str]:
    """从 translation 提取 (pos, meaning)。

    - 行首词性前缀（n./vt./a. 等）映射为知岸词性，按出现顺序去重、用 / 连接；
    - 每行去掉词性前缀与 [医]/[计]/[法] 等领域标签；
    - "[网络]" 网络释义段整体丢弃；
    - 多行释义用「；」连接。
    """
    pos_forms: list[str] = []
    meanings: list[str] = []
    # ECDICT 的多行分隔是字面 "\n"（反斜杠+n 两字符），先归一化为真换行再拆行
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
                pass  # 构词法标记（pref/suf/abbr）：剥离前缀，不计入词性
            else:
                unmapped_pos[abbrev] += 1
                # 未知词性：保底，把前缀并入释义原文
                content = f"{abbrev}. {content}".strip()
        else:
            content = line

        # 去掉行首领域标签 [医]/[计]/[法]/[化] 等
        content = re.sub(r"^\[[^\]]+\]\s*", "", content).strip()
        if content:
            meanings.append(content)

    return "/".join(pos_forms), "；".join(meanings)


def difficulty_of(collins_raw: object, bnc_raw: object, frq_raw: object) -> int:
    """按柯林斯星级 + 词频综合判断难度 1/2/3。"""
    collins = _int(collins_raw)
    bnc = _int(bnc_raw)
    frq = _int(frq_raw)
    if (collins is not None and collins >= 4) or (bnc is not None and bnc <= 5000):
        return 1
    if (collins == 3) or (bnc is not None and bnc <= 30000) or (frq is not None and frq <= 30000):
        return 2
    return 3


# ---------- 第二遍筛选 ----------


def build() -> tuple[dict[str, dict], Counter]:
    """按 KAOYAN_TAG 筛选，清洗、去重。返回 {word: row} 与统计。"""
    kept: dict[str, dict] = {}
    stat: Counter = Counter()
    with ECDICT_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if KAOYAN_TAG not in (row.get("tag") or "").split():
                continue
            stat["tag_matched"] += 1
            word = clean_word(row.get("word"))
            if word is None:
                stat["excluded_invalid"] += 1
                continue
            if word in kept:
                stat["dedup"] += 1
                continue
            kept[word] = row
    stat["kept"] = len(kept)
    return kept, stat


def to_rows(kept: dict[str, dict]) -> tuple[list[list], int, int]:
    """映射成知岸 CSV 行，返回 (行列表, 音标缺失数, 释义缺失数)。"""
    rows: list[list] = []
    phonetic_missing = 0
    meaning_missing = 0
    for word in sorted(kept):
        r = kept[word]
        phonetic = (r.get("phonetic") or "").strip()
        # ECDICT 音标误用西里尔 ә(U+04D9) 表示 schwa，统一为 IPA ə(U+0259)
        phonetic = phonetic.replace("ә", "ə")
        pos, meaning = extract_pos_meaning(r.get("translation") or "")
        if not phonetic:
            phonetic_missing += 1
        if not meaning:
            meaning_missing += 1
        difficulty = difficulty_of(r.get("collins"), r.get("bnc"), r.get("frq"))
        rows.append([word, phonetic, pos, meaning, "", "", "考研", difficulty])
    return rows, phonetic_missing, meaning_missing


def write_output(rows: list[list]) -> None:
    """写出 UTF-8 BOM + CRLF 的 CSV，表头与 seed_words.csv 一致。"""
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        f.write("﻿")  # BOM
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(HEADER)
        w.writerows(rows)


# ---------- 主流程 ----------


def _print_table(title: str, counter: Counter, highlight: set[str] | None = None) -> None:
    print(f"\n===== {title} =====")
    for value, count in counter.most_common():
        mark = "  <-- 考研候选" if highlight and value in highlight else ""
        print(f"  {value!r:20s} {count:>8}{mark}")


def main() -> None:
    download()

    # 1) 探测：tag 唯一值 + 出现次数
    tag_counter = scan()
    kaoyan_candidates = {t for t in tag_counter if any(k in t for k in ("ky", "kaoyan", "研", "考"))}
    _print_table(f"tag 唯一值（共 {len(tag_counter)} 种）", tag_counter, kaoyan_candidates)

    print(f"\n[筛选] 当前 KAOYAN_TAG = {KAOYAN_TAG!r}，请核对上方 tag 分布确认。")

    # 2) 筛选 + 映射
    kept, stat = build()
    rows, phonetic_missing, meaning_missing = to_rows(kept)
    write_output(rows)

    # 3) 统计
    print("\n===== 筛选统计 =====")
    print(f"  tag 命中（含考研标签的原始词条）: {stat['tag_matched']}")
    print(f"  排除（多词/含数字符号等非单词） : {stat['excluded_invalid']}")
    print(f"  去重（同一单词多条）             : {stat['dedup']}")
    print(f"  最终保留单词数                   : {stat['kept']}")

    diff_counter = Counter(r[7] for r in rows)
    print("\n===== difficulty 分布 =====")
    for d in (1, 2, 3):
        print(f"  {d}: {diff_counter.get(d, 0)}")

    print("\n===== 缺失统计 =====")
    print(f"  音标缺失: {phonetic_missing}")
    print(f"  释义缺失: {meaning_missing}")

    if unmapped_pos:
        print("\n===== 未映射的 translation 词性前缀（需核对 POS_FORM_MAP） =====")
        for letter, count in unmapped_pos.most_common():
            print(f"  {letter!r}: {count}")

    print(f"\n===== 输出文件 =====")
    print(f"  {OUT_CSV}（{OUT_CSV.stat().st_size / 1024:.1f} KB）")

    print("\n===== 前 10 个词示例 =====")
    print(f"  {'word':<16}{'phonetic':<16}{'pos':<10}meaning")
    for r in rows[:10]:
        meaning = r[3] if len(r[3]) <= 36 else r[3][:33] + "..."
        print(f"  {r[0]:<16}{r[1]:<16}{r[2]:<10}{meaning}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
