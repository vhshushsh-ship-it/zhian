from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  确保模型注册到 metadata
from .config import settings
from .database import Base, engine
from .routers import auth, notes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动建表（幂等，不会覆盖已有数据）
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="login-demo API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(notes.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
