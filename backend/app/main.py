from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  确保模型注册到 metadata
from .config import settings
from .database import engine
from .routers import auth, notes





app = FastAPI(title="login-demo API")

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
