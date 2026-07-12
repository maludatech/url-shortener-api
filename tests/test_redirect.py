from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import URL


def test_redirect_follows_to_long_url(client: TestClient) -> None:
    created = client.post("/shorten", json={"long_url": "https://example.com/target"}).json()

    response = client.get(f"/{created['short_code']}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/target"


def test_redirect_increments_click_count(client: TestClient, db_session: Session) -> None:
    created = client.post("/shorten", json={"long_url": "https://example.com/counted"}).json()
    code = created["short_code"]

    client.get(f"/{code}", follow_redirects=False)
    client.get(f"/{code}", follow_redirects=False)
    client.get(f"/{code}", follow_redirects=False)

    url = db_session.query(URL).filter(URL.short_code == code).one()
    assert url.click_count == 3


def test_redirect_unknown_code_returns_404(client: TestClient) -> None:
    response = client.get("/this-code-does-not-exist", follow_redirects=False)
    assert response.status_code == 404
