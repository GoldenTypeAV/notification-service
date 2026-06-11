import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_subscriber(client: AsyncClient):
    response = await client.post("/api/v1/subscribers/")
    assert response.status_code == 201
    data = response.json()
    subscriber_id = data["id"]
    assert data["is_active"] is True

    response = await client.get(f"/api/v1/subscribers/{subscriber_id}")
    assert response.status_code == 200
    assert response.json()["id"] == subscriber_id


@pytest.mark.asyncio
async def test_invalid_email_contact_rejected(client: AsyncClient):
    resp = await client.post("/api/v1/subscribers/")
    subscriber_id = resp.json()["id"]
    resp = await client.post(
        f"/api/v1/subscribers/{subscriber_id}/contacts",
        json={"channel": "email", "contact": "not-an-email"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_bulk_notification_creates_history(client: AsyncClient):
    resp = await client.post("/api/v1/subscribers/")
    subscriber_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/subscribers/{subscriber_id}/contacts",
        json={"channel": "email", "contact": "user@example.com", "is_verified": True},
    )
    assert resp.status_code == 201

    resp = await client.post(
        "/api/v1/notifications/bulk",
        json={
            "channel": "email",
            "content": "Hello",
            "subscriber_ids": [subscriber_id],
            "priority": "high",
        },
    )
    assert resp.status_code == 202
    assert resp.json()["accepted"] == 1

    resp = await client.get(f"/api/v1/notifications/history/{subscriber_id}")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 1
    assert history[0]["status"] == "queued"
    assert history[0]["channel"] == "email"


@pytest.mark.asyncio
async def test_bulk_rejects_inactive_recipients(client: AsyncClient):
    resp = await client.post(
        "/api/v1/notifications/bulk",
        json={
            "channel": "email",
            "content": "Hello",
            "subscriber_ids": [999999],
            "priority": "normal",
        },
    )
    assert resp.status_code == 400
