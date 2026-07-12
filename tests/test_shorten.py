from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import URL


def test_shorten_creates_a_short_link(client: TestClient) -> None:
    response = client.post("/shorten", json={"long_url": "https://example.com/some/path"})
    assert response.status_code == 201

    body = response.json()
    assert body["long_url"] == "https://example.com/some/path"
    assert body["click_count"] == 0
    assert body["short_code"] in body["short_url"]


def test_shorten_rejects_invalid_url(client: TestClient) -> None:
    response = client.post("/shorten", json={"long_url": "not-a-url"})
    assert response.status_code == 422


def test_shorten_generates_distinct_codes(client: TestClient, db_session: Session) -> None:
    first = client.post("/shorten", json={"long_url": "https://example.com/a"}).json()
    second = client.post("/shorten", json={"long_url": "https://example.com/b"}).json()

    assert first["short_code"] != second["short_code"]

    codes = {first["short_code"], second["short_code"]}
    stored = db_session.query(URL).filter(URL.short_code.in_(codes)).count()
    assert stored == 2
