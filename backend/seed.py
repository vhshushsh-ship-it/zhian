"""词库导入脚本：读取考研 / 四级 / 六级三个 CSV 写入 MySQL，幂等可重复执行。

用法（在 backend 目录下）：
    python seed.py

说明：
- 复用 app.database 的 SessionLocal 建立会话（其引擎通过 app.config 从
  backend/.env 读取 DATABASE_URL）。
- 三本词书分别对应三个 CSV，tags 字段为知岸内部标签（考研 / 四级 / 六级）。
- 按 words.word 唯一字段做 upsert：存在则更新 phonetic / tags / difficulty，
  不存在则新建。
- tags 做并集合并：同一单词出现在多个词书时同时保留多个标签（如「考研,四级」），
  保证重叠词不被覆盖丢失。
- 释义按中文分号「；」拆分为多条 word_definitions；例句写入 1 条；两者均先
  清空再重建，保证重复执行不产生重复数据。
"""

import csv
import sys
from pathlib import Path

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Word, WordDefinition, WordExample

# 控制台统一 UTF-8，避免 Windows GBK 编码下中文打印报错/乱码
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent

# 词书：知岸标签 -> CSV 路径
BOOK_CSVS = [
    ("考研", BASE_DIR / "seed_words.csv"),
    ("四级", BASE_DIR / "cet4_words.csv"),
    ("六级", BASE_DIR / "cet6_words.csv"),
]


def merge_tags(existing: str | None, incoming: str) -> str:
    """并集合并逗号分隔的 tags，保持原顺序并去重。"""
    parts = [p.strip() for p in (existing or "").split(",") if p.strip()]
    for t in (incoming or "").split(","):
        t = t.strip()
        if t and t not in parts:
            parts.append(t)
    return ",".join(parts)


def import_csv(db, path: Path, book_tag: str) -> tuple[int, int]:
    """导入单个词书 CSV，返回 (新增数, 更新数)。"""
    if not path.exists():
        print(f"[跳过] 未找到 {path.name}")
        return 0, 0

    added = 0
    updated = 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word_text = (row["word"] or "").strip()
            if not word_text:
                continue

            phonetic = (row["phonetic"] or "").strip()
            pos = (row["pos"] or "").strip()
            meaning = (row["meaning"] or "").strip()
            example_en = (row["example_en"] or "").strip()
            example_zh = (row["example_zh"] or "").strip()
            tags = (row["tags"] or "").strip() or book_tag
            difficulty = int(row["difficulty"] or "1")

            # 1) 按 word 唯一字段 upsert
            word = db.scalar(select(Word).where(Word.word == word_text))
            if word is None:
                word = Word(word=word_text)
                added += 1
            else:
                updated += 1
            word.phonetic = phonetic
            # tags 并集合并，避免多词书重叠词被后者覆盖
            word.tags = merge_tags(word.tags, tags)
            word.difficulty = difficulty
            db.add(word)
            db.flush()  # 确保新词拿到自增 id

            # 2) 释义：先清空旧记录，再按「；」拆分重建
            for d in db.scalars(
                select(WordDefinition).where(WordDefinition.word_id == word.id)
            ).all():
                db.delete(d)
            db.flush()

            meanings = [m.strip() for m in meaning.split("；") if m.strip()]
            for idx, m in enumerate(meanings):
                db.add(
                    WordDefinition(
                        word_id=word.id,
                        pos=pos,
                        meaning=m,
                        order_index=idx,
                    )
                )

            # 3) 例句：先清空旧记录，再写入 1 条
            for e in db.scalars(
                select(WordExample).where(WordExample.word_id == word.id)
            ).all():
                db.delete(e)
            db.flush()

            if example_en:
                db.add(
                    WordExample(
                        word_id=word.id,
                        en=example_en,
                        zh=example_zh or None,
                        order_index=0,
                    )
                )

    return added, updated


def main() -> None:
    total_added = 0
    total_updated = 0

    with SessionLocal() as db:
        for book_tag, path in BOOK_CSVS:
            added, updated = import_csv(db, path, book_tag)
            total_added += added
            total_updated += updated
            print(f"[{book_tag}] 导入完成：新增 {added} 词，更新 {updated} 词")
        db.commit()

        # 统计各词书词数（含重叠，按 tags LIKE 匹配）
        def count_by_tag(tag: str) -> int:
            return (
                db.query(func.count(Word.id))
                .filter(Word.tags.like(f"%{tag}%"))
                .scalar()
                or 0
            )

        kaoyan = count_by_tag("考研")
        cet4 = count_by_tag("四级")
        cet6 = count_by_tag("六级")

    print(f"\n本次导入：新增 {total_added} 词，更新 {total_updated} 词")
    print(f"词库总量：考研 {kaoyan} 词、四级 {cet4} 词、六级 {cet6} 词")


if __name__ == "__main__":
    main()
