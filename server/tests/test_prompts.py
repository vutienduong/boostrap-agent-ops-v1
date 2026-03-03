import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_prompt_versions(client: AsyncClient):
    # Create first version
    resp = await client.post(
        "/v1/prompts",
        params={"project_id": "proj_test"},
        json={"key": "system_prompt", "version": "1", "content": "You are a helpful assistant."},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["key"] == "system_prompt"
    assert data["version"] == "1"
    prompt_id = data["id"]

    # Create second version
    await client.post(
        "/v1/prompts",
        params={"project_id": "proj_test"},
        json={"key": "system_prompt", "version": "2", "content": "You are an expert assistant."},
    )

    # List all versions for key
    resp = await client.get(
        "/v1/prompts",
        params={"project_id": "proj_test", "key": "system_prompt"},
    )
    assert resp.status_code == 200
    versions = resp.json()["versions"]
    assert len(versions) == 2

    # Get specific version
    resp = await client.get(f"/v1/prompts/{prompt_id}")
    assert resp.status_code == 200
    assert resp.json()["content"] == "You are a helpful assistant."


@pytest.mark.asyncio
async def test_get_prompt_not_found(client: AsyncClient):
    resp = await client.get("/v1/prompts/01JNONEXISTENT0000000000")
    assert resp.status_code == 404
