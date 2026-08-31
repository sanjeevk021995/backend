import json
import logging
import sys
import time
from fastapi import Request, FastAPI
from fastapi.responses import Response, JSONResponse
from sqlalchemy import event
from sqlalchemy.engine import Engine
import structlog
import jwt 


def setup_logging(debug: bool = False):
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    processors = shared_processors + (
        [structlog.dev.ConsoleRenderer(colors=True)]
        if debug
        else [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    )

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Intercept standard library logs (uvicorn, sqlalchemy, etc.)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if debug else logging.INFO,
    )


# --- 1. AUTOMATIC SQLALCHEMY LOGGING ---
def setup_db_logging(engine: Engine, slow_query_threshold_ms: float = 500.0):
    db_logger = structlog.get_logger("app.db")

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.time())

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total_time = (time.time() - conn.info["query_start_time"].pop()) * 1000

        # Log slow queries automatically
        if total_time >= slow_query_threshold_ms:
            db_logger.warning(
                "slow_database_query",
                duration_ms=round(total_time, 2),
                statement=statement,
            )


# --- 2. FASTAPI MIDDLEWARE & EXCEPTION HANDLER ---
log = structlog.get_logger("app.api")

 # Ensure PyJWT is installed (pip install PyJWT)


log = structlog.get_logger("app.api")

def register_logging_app(app: FastAPI):
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        structlog.contextvars.clear_contextvars()

        # 1. Bind Clinic ID from Params or Headers
        clinic_id = request.query_params.get("clinic_id") or request.headers.get("X-Clinic-ID")
        if clinic_id:
            structlog.contextvars.bind_contextvars(clinic_id=clinic_id)

        # 2. Extract and Bind user_id from Authorization Header for ALL Requests
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Decodes JWT payload WITHOUT verifying signature just to read 'sub' for logs
                payload = jwt.decode(token, options={"verify_signature": False})
                user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
                if user_id:
                    structlog.contextvars.bind_contextvars(user_id=str(user_id))
            except Exception:
                pass  # Ignore invalid token formatting at logging stage

        start_time = time.time()
        response = await call_next(request)
        duration = round((time.time() - start_time) * 1000, 2)

        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration,
        }

        # Safely capture response error payload for 4xx/5xx responses
        if response.status_code >= 400:
            try:
                body_bytes = b"".join([chunk async for chunk in response.body_iterator])
                response = Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

                parsed_body = json.loads(body_bytes.decode("utf-8"))
                log_data["response_error_detail"] = parsed_body
            except Exception:
                log_data["response_error_detail"] = "Could not parse response body"

            log.error("http_request_failed", **log_data)
        else:
            log.info("http_request_finished", **log_data)

        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        log.error(
            "unhandled_server_error",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )