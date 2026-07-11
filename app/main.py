from fastapi import FastAPI

from app.routers import urls

app = FastAPI(title="URL Shortener API")
app.include_router(urls.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
