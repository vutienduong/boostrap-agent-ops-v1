from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ingest import router as ingest_router
from app.api.metrics import router as metrics_router
from app.api.runs import router as runs_router
from app.core.seed import seed_default_project


@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed_default_project()
    yield


app = FastAPI(title="AgentOps", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(runs_router)
app.include_router(metrics_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
