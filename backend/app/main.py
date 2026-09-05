from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import admin, auth, english_speaking, tts

app = FastAPI(title="zhian API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(english_speaking.router, prefix="/api")
app.include_router(tts.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
