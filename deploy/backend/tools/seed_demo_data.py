"""演示数据预置脚本：为演示用户 demo@zhian.com 写入示例学习数据（幂等）。

用法（在 backend 目录下）：
    python tools/seed_demo_data.py

说明：
- 复用 app.database 的 SessionLocal 建立会话；
- 调用 app.demo.seed_demo_data，可重复执行，已存在的数据不重复插入；
- 若词库 / 文章库尚未导入，会先跳过相应部分（不影响其它数据预置）。
"""

import sys
from pathlib import Path

# 将 backend 目录加入 sys.path，使 `app` 包可导入（脚本位于 tools/ 子目录）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.demo import seed_demo_data  # noqa: E402


def main() -> None:
    with SessionLocal() as db:
        seed_demo_data(db)
    print("演示数据预置完成（demo@zhian.com）")


if __name__ == "__main__":
    main()
