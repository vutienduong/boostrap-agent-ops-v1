import gzip
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.schemas import IngestEvent, IngestResponse
from app.services.ingest_store import store_raw_events
from app.services.normalizer import normalize_event

router = APIRouter(prefix="/v1", tags=["ingest"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_events(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    body = await request.body()

    if request.headers.get("content-encoding") == "gzip":
        body = gzip.decompress(body)

    try:
        data = json.loads(body)
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"accepted": 0, "rejected": 1, "errors": ["Invalid JSON body"]},
        )

    # Validate each event with Pydantic
    valid_events = []
    rejected = 0
    errors = []
    for item in data:
        try:
            event = IngestEvent.model_validate(item)
            valid_events.append(event.model_dump(mode="json"))
        except Exception as e:
            rejected += 1
            errors.append(str(e))

    accepted, rej2, errs2 = await store_raw_events(session, valid_events)
    rejected += rej2
    errors.extend(errs2)

    for raw in valid_events:
        try:
            await normalize_event(session, raw)
        except Exception:
            pass

    return IngestResponse(accepted=accepted, rejected=rejected, errors=errors)
