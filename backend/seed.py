"""词库导入脚本：读取 seed_words.csv 写入 MySQL，幂等可重复执行。

用法（在 backend 目录下）：
    python seed.py

说明：
- 复用 app.database 的 SessionLocal 建立会话（其引擎通过 app.config 从
  backend/.env 读取 DATABASE_URL）。
- 按 words.word 唯一字段做 upsert：存在则更新 phonetic/tags/difficulty，
  不存在则新建。
- 释义按中文分号「；」拆分为多条 word_definitions（词性相同，order_index
  递增）；已存在的词先清空旧释义再重建，保证重复执行不产生重复数据。
- 每个词写入 1 条 word_examples（英文例句 + 中文翻译），同样先清空再重建。
- 纯词库数据，不依赖用户表，所有用户共享。
"""

import csv
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Word, WordDefinition, WordExample

# CSV 与本脚本同目录
CSV_PATH = Path(__file__).resolve().parent / "seed_words.csv"


def main() -> None:
    added = 0
    updated = 0
    definition_count = 0
    example_count = 0

    with SessionLocal() as db:
        # utf-8-sig 会自动去掉 BOM，避免第一列表头带上
        with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
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
                tags = (row["tags"] or "").strip()
                difficulty = int(row["difficulty"] or "1")

                # 1) 按 word 唯一字段 upsert
                word = db.scalar(select(Word).where(Word.word == word_text))
                if word is None:
                    word = Word(word=word_text)
                    added += 1
                else:
                    updated += 1
                word.phonetic = phonetic
                word.tags = tags or "考研"
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
                    definition_count += 1

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
                    example_count += 1

        db.commit()

    print(f"导入完成：新增 {added} 词，更新 {updated} 词")
    print(f"释义总数：{definition_count}，例句总数：{example_count}")


if __name__ == "__main__":
    main()
