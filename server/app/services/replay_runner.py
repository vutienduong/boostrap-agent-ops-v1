"""
Replay runner — re-executes LLM spans from a source run with overrides.

For each LLM span in the source run (ordered by started_at):
  - Extract the messages/prompt from input_json
  - Call the LLM with overrides applied (model, temperature)
  - Store the result as a new span in a new run

Tool spans are copied as-is with status="skipped".
"""
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.models.tables import Replay, Run, Span


async def execute_replay(session: AsyncSession, replay_id: str) -> None:
    # Load replay record
    result = await session.execute(select(Replay).where(Replay.id == replay_id))
    replay = result.scalar_one_or_none()
    if not replay:
        return

    # Mark as running
    replay.status = "running"
    await session.commit()

    try:
        # Load source run + spans
        result = await session.execute(select(Run).where(Run.id == replay.source_run_id))
        source_run = result.scalar_one_or_none()
        if not source_run:
            raise ValueError(f"Source run {replay.source_run_id} not found")

        result = await session.execute(
            select(Span)
            .where(Span.run_id == replay.source_run_id)
            .order_by(Span.started_at.nullslast(), Span.id)
        )
        source_spans = result.scalars().all()

        overrides = replay.overrides or {}
        override_model = overrides.get("model")
        override_temperature = overrides.get("temperature")

        # Create new run
        new_run_id = str(ULID())
        new_run = Run(
            id=new_run_id,
            project_id=source_run.project_id,
            name=f"replay:{source_run.name or source_run.id}",
            status="running",
            started_at=datetime.now(timezone.utc),
            tags={"replay_of": replay.source_run_id, **(source_run.tags or {})},
        )
        session.add(new_run)
        await session.flush()

        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_cost = 0.0

        for source_span in source_spans:
            new_span_id = str(ULID())
            span_started = datetime.now(timezone.utc)

            if source_span.type != "llm":
                # Non-LLM spans: copy with skipped status
                new_span = Span(
                    id=new_span_id,
                    run_id=new_run_id,
                    parent_span_id=None,
                    type=source_span.type,
                    name=source_span.name,
                    started_at=span_started,
                    ended_at=span_started,
                    duration_ms=0,
                    status="skipped",
                    model=source_span.model,
                    tokens_prompt=0,
                    tokens_completion=0,
                    cost_usd=0.0,
                    input_json=source_span.input_json,
                    output_json={"note": "skipped in replay"},
                )
                session.add(new_span)
                continue

            # LLM span: re-execute
            model = override_model or source_span.model or "gpt-4o-mini"
            input_data = source_span.input_json or {}
            messages = _extract_messages(input_data)

            output_text = None
            prompt_tokens = 0
            completion_tokens = 0
            span_cost = 0.0
            span_status = "success"
            error_info = None

            try:
                result_data = await _call_llm(
                    model=model,
                    messages=messages,
                    temperature=override_temperature,
                )
                output_text = result_data.get("text")
                prompt_tokens = result_data.get("prompt_tokens", 0)
                completion_tokens = result_data.get("completion_tokens", 0)
                span_cost = result_data.get("cost_usd", 0.0)
            except Exception as e:
                span_status = "fail"
                error_info = {"message": str(e), "type": type(e).__name__}

            span_ended = datetime.now(timezone.utc)
            duration_ms = int((span_ended - span_started).total_seconds() * 1000)

            new_span = Span(
                id=new_span_id,
                run_id=new_run_id,
                parent_span_id=None,
                type="llm",
                name=source_span.name,
                started_at=span_started,
                ended_at=span_ended,
                duration_ms=duration_ms,
                status=span_status,
                model=model,
                tokens_prompt=prompt_tokens,
                tokens_completion=completion_tokens,
                cost_usd=span_cost,
                input_json={"messages": messages},
                output_json={"text": output_text} if output_text else None,
                error_json=error_info,
            )
            session.add(new_span)
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            total_cost += span_cost

        # Finish new run
        run_ended = datetime.now(timezone.utc)
        new_run.status = "success"
        new_run.ended_at = run_ended
        new_run.duration_ms = int((run_ended - new_run.started_at).total_seconds() * 1000)
        new_run.total_prompt_tokens = total_prompt_tokens
        new_run.total_completion_tokens = total_completion_tokens
        new_run.total_cost_usd = total_cost

        # Update replay record
        replay.new_run_id = new_run_id
        replay.status = "done"
        await session.commit()

    except Exception as e:
        replay.status = "failed"
        await session.commit()
        raise


def _extract_messages(input_data: dict) -> list[dict]:
    """Extract messages array from stored span input."""
    # Handle nested: {"inline": {"messages": [...]}}
    if "inline" in input_data and "messages" in input_data["inline"]:
        return input_data["inline"]["messages"]
    # Handle flat: {"messages": [...]}
    if "messages" in input_data:
        return input_data["messages"]
    # Fallback: wrap whatever text we have as a user message
    text = str(input_data) if input_data else "replay"
    return [{"role": "user", "content": text}]


async def _call_llm(model: str, messages: list[dict], temperature: float | None) -> dict:
    """
    Call LLM and return result dict.
    Supports OpenAI and Anthropic models based on model name prefix.
    Requires OPENAI_API_KEY or ANTHROPIC_API_KEY in environment.
    """
    import os

    kwargs: dict = {"model": model, "messages": messages}
    if temperature is not None:
        kwargs["temperature"] = temperature

    if model.startswith("claude"):
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        # Anthropic uses max_tokens, required
        kwargs["max_tokens"] = 1024
        # Anthropic doesn't support "system" in messages array — extract it
        system_msgs = [m for m in messages if m.get("role") == "system"]
        user_msgs = [m for m in messages if m.get("role") != "system"]
        if system_msgs:
            kwargs["system"] = system_msgs[0]["content"]
        kwargs["messages"] = user_msgs
        resp = client.messages.create(**kwargs)
        text = resp.content[0].text if resp.content else ""
        return {
            "text": text,
            "prompt_tokens": resp.usage.input_tokens,
            "completion_tokens": resp.usage.output_tokens,
            "cost_usd": 0.0,  # simplified
        }
    else:
        import openai
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        resp = client.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content if resp.choices else ""
        usage = resp.usage
        return {
            "text": text,
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "cost_usd": 0.0,  # simplified
        }
