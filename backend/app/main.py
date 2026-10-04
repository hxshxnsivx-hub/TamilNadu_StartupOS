"""FastAPI application factory (Task 1.9 base).

Boots the API, wires structured logging, standardized errors, request-id and
rate-limit middleware, and mounts the API v1 routers. Domain routers (auth,
profiles, startups, ideation) attach here as later tasks land.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware
from app.routers import (
    auth,
    b2b,
    banking,
    ecosystem,
    funding,
    health,
    ideation,
    news,
    schemes,
    verification,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger("startup")
    log.info("app.start", app=settings.app_name, env=settings.app_env)
    # DB / Redis / S3 connection pools initialize in Task 5 (db.session).
    yield
    log.info("app.stop")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Vanigam — Tamil Nadu StartupOS",
        version="0.1.0",
        description="Multi-agent AI platform for Tamil Nadu startup founders.",
        lifespan=lifespan,
    )

    # Middleware (outermost first): request-id, then rate limit.
    app.add_middleware(
        RateLimitMiddleware,
        per_user_per_min=settings.rate_limit_per_user_per_min,
        global_per_min=settings.rate_limit_global_per_min,
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(ideation.router)
    app.include_router(schemes.router)
    app.include_router(verification.router)
    app.include_router(b2b.router)
    app.include_router(funding.router)
    app.include_router(news.router)
    app.include_router(banking.router)
    app.include_router(ecosystem.router)
    # Later: profiles/startups persistence ...

    return app


app = create_app()
