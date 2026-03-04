import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import skill
from app.services.playbook import load_playbooks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(application: FastAPI):
    load_playbooks()
    yield


app = FastAPI(
    title="성북구청 민원 상담 챗봇 V1",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(skill.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
