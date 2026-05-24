from fastapi import FastAPI

from agnost_analytics.core.config import get_settings
from agnost_analytics.api.routes import router as api_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router)

    return app


app = create_app()
