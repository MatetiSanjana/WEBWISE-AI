import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.errors import ResearchError
from app.models import db
from app.utils.logging import configure_logging

log = logging.getLogger("webwise")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    configure_logging(s.log_level)
    db.init_db()
    interrupted = db.mark_interrupted()
    if interrupted:
        log.warning("marked %d interrupted job(s) as failed", interrupted)
    log.info(
        "Webwise AI backend ready (model=%s, tavily=%s, gemini=%s)",
        s.gemini_model, "configured" if s.tavily_configured else "MISSING", "configured" if s.gemini_configured else "MISSING",
    )
    yield


def create_app() -> FastAPI:
    docs = get_settings().enable_docs
    app = FastAPI(
        title="Webwise AI", version="0.1.0", lifespan=lifespan,
        docs_url="/docs" if docs else None, redoc_url=None, openapi_url="/openapi.json" if docs else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Client-Id"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith("/api"):
            response.headers.setdefault("Cache-Control", "no-store")  # research data is private
        return response

    @app.exception_handler(ResearchError)
    async def research_error_handler(_: Request, exc: ResearchError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "retryable": exc.retryable}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        msgs = [f"{'.'.join(str(p) for p in e['loc'][1:]) or 'request'}: {e['msg'].removeprefix('Value error, ')}" for e in exc.errors()]
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "INVALID_INPUT", "message": "; ".join(msgs), "retryable": False}},
        )

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):
        log.exception("unhandled error")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Unexpected server error.", "retryable": True}},
        )

    app.include_router(router)
    return app


app = create_app()
