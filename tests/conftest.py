import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app


@pytest.fixture(autouse=True)
def _disable_rate_limiting():
    app.state.limiter.enabled = False
    yield
    app.state.limiter.enabled = True


@pytest.fixture
def db_session():
    """Wrap each test in an outer transaction that's always rolled back,
    even though route handlers call db.commit() themselves. Each commit
    ends the current SAVEPOINT; the listener immediately opens a new one,
    so the outer transaction never actually finalizes."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess: Session, trans) -> None:
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)
