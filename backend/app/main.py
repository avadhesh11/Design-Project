from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .database import engine, Base
from .routes import auth, workspaces, documents, chat, tasks, ai, github, flows, dashboard
import logging

logger = logging.getLogger(__name__)

from sqlalchemy import text

# Create tables & ensure new columns exist
try:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for col_sql in [
            "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS ai_provider VARCHAR DEFAULT 'gemini'",
            "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS ai_model VARCHAR DEFAULT 'gemini-2.5-flash'",
            "ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS ai_ollama_url VARCHAR DEFAULT 'http://localhost:11434'",
            "ALTER TABLE users ALTER COLUMN password DROP NOT NULL",
        ]:
            try:
                conn.execute(text(col_sql))
            except Exception as migrate_err:
                logger.debug(f"Migration notice: {migrate_err}")
except Exception as e:
    logger.warning(f"Could not initialize or migrate tables: {e}")

app = FastAPI(title="Orbit AI API")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000", "https://orbit-avadhesh.vercel.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(workspaces.router, prefix="/api") 
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(github.router, prefix="/api")
app.include_router(flows.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")



from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None)
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.get("/api/health")
def health(response: Response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return {
        "status": "ok",
        "services": {
            "api": "operational",
            "database": "operational",
            "agent_engine": "operational"
        }
    }
