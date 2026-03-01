from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.schemas import IngestEvent, IngestResponse
from app.services.ingest_store import store_raw_events
from app.services.normalizer import normalize_event

router = APIRouter(prefix="/v1", tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_events(
    events: list[IngestEvent],
    session: AsyncSession = Depends(get_db),
):
    raw_dicts = [e.model_dump(mode="json") for e in events]

    accepted, rejected, errors = await store_raw_events(session, raw_dicts)

    for raw in raw_dicts:
        try:
            await normalize_event(session, raw)
        except Exception:
            pass  # normalization failure must not block ingest

    return IngestResponse(accepted=accepted, rejected=rejected, errors=errors)
