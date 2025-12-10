"""
Main FastAPI Application
Entry point for KUBERA Stock Analysis Chatbot
"""
import uvicorn

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

import logging
import sys
from datetime import datetime

from app.core.config import settings
from app.core.database import init_db, close_db
from app.mcp.client import kubera_mcp_client
from app.background.scheduler import background_scheduler
from app.exceptions.handlers import (
    kubera_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from app.exceptions.custom_exceptions import KuberaException

# Routers
from app.api.routes import (
    auth_routes,
    user_routes,
    portfolio_routes,
    chat_routes,
    admin_routes,
    websocket_routes,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("kubera.log"),
    ],
)

logger = logging.getLogger(__name__)

from app.api.routes.websocket_routes import router as ws_router


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown."""

    # STARTUP
    logger.info("=" * 80)
    logger.info(" STARTING KUBERA STOCK ANALYSIS CHATBOT")
    logger.info("=" * 80)

    startup_errors = []

    try:
        # STEP 1: DATABASE
        logger.info(" Step 1/3: Initializing database connection pool...")
        await init_db()
        logger.info(" Database connection established")

        # STEP 2: MCP CLIENT
        logger.info(" Step 2/3: Initializing MCP Client (connecting to 5 servers)...")

        try:
            await kubera_mcp_client.initialize()
            logger.info(" MCP Client initialized successfully")

            health = kubera_mcp_client.get_health_status()
            logger.info(f" MCP Health: {health['total_servers']} servers, {health['total_tools']} tools")
            logger.info(f" Available tools: {', '.join(health['tools_available'][:10])}...")
        except Exception as e:
            logger.error(f" MCP Client initialization failed: {e}")
            startup_errors.append(("MCP Client", str(e)))

        # STEP 3: BACKGROUND SCHEDULER
        logger.info(" Step 3/3: Starting background job scheduler...")

        try:
            await background_scheduler.start()
            logger.info(" Background scheduler started")

            scheduler_stats = background_scheduler.get_statistics()
            logger.info(f" Scheduler: {scheduler_stats['total_jobs']} jobs scheduled")
        except Exception as e:
            logger.error(f" Background scheduler failed to start: {e}")
            startup_errors.append(("Background Scheduler", str(e)))

        # SUMMARY
        logger.info("=" * 80)

        if startup_errors:
            logger.warning("  KUBERA STARTED WITH WARNINGS")
            for component, error in startup_errors:
                logger.warning(f"  - {component}: {error}")
        else:
            logger.info(" KUBERA IS READY TO SERVE!")

        logger.info("=" * 80)
        logger.info(" Documentation: http://localhost:8000/docs")
        logger.info(" WebSocket: ws://localhost:8000/ws/chat")
        logger.info(" Health Check: http://localhost:8000/health")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f" CRITICAL STARTUP FAILURE: {e}", exc_info=True)
        raise

    yield

    # ========================================================================
    # SHUTDOWN
    # ========================================================================

    logger.info("=" * 80)
    logger.info(" SHUTTING DOWN KUBERA")
    logger.info("=" * 80)

    try:
        # STEP 1: STOP SCHEDULER
        logger.info(" Step 1/3: Stopping background scheduler...")
        try:
            await background_scheduler.shutdown()
            logger.info(" Background scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")

        # STEP 2: CLOSE MCP
        logger.info(" Step 2/3: Closing MCP Client connections...")
        try:
            await kubera_mcp_client.shutdown()
            logger.info(" MCP Client closed")
        except Exception as e:
            logger.error(f"Error closing MCP client: {e}")

        # STEP 3: CLOSE DATABASE
        logger.info(" Step 3/3: Closing database connections...")
        try:
            await close_db()
            logger.info(" Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")

        logger.info("=" * 80)
        logger.info(" KUBERA SHUTDOWN COMPLETE")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f" SHUTDOWN ERROR: {e}", exc_info=True)


# ============================================================================
# CREATE APP
# ============================================================================

app = FastAPI(
    title="KUBERA Stock Analysis Chatbot",
    description="""
    ##  KUBERA - AI-Powered Indian Stock Market Analysis Platform
    ... (same long description unchanged)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Include WebSocket router
app.include_router(ws_router)

# ============================================================================
# MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(f"  {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"  {response.status_code}")
    return response


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

app.add_exception_handler(KuberaException, kubera_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# ============================================================================
# ROUTERS
# ============================================================================

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(portfolio_routes.router)
app.include_router(chat_routes.router)
app.include_router(admin_routes.router)
app.include_router(websocket_routes.router)


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"], summary="API Root")
async def root():
    return {
        "message": "Welcome to KUBERA Stock Analysis Chatbot API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "documentation": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "websocket": "ws://localhost:8000/ws/chat",
        },
        "features": {
            "rest_endpoints": 42,
            "websocket_endpoints": 1,
            "mcp_servers": 5,
            "mcp_tools": 44,
            "database_tables": 15,
            "background_jobs": 4,
        },
    }


@app.get("/health", tags=["Root"], summary="Health Check")
async def health_check():
    mcp_health = kubera_mcp_client.get_health_status()
    scheduler_health = background_scheduler.get_statistics()

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api": {"status": "operational", "version": "1.0.0"},
        "mcp": {
            "initialized": mcp_health["initialized"],
            "servers": mcp_health["total_servers"],
            "tools": mcp_health["total_tools"],
            "status": "operational" if mcp_health["initialized"] else "not_initialized",
        },
        "database": {"status": "connected"},
        "scheduler": {
            "running": scheduler_health["running"],
            "total_jobs": scheduler_health["total_jobs"],
            "status": "operational" if scheduler_health["running"] else "not_running",
        },
    }


@app.get("/mcp/tools", tags=["MCP"], summary="List MCP Tools")
async def list_mcp_tools():
    if not kubera_mcp_client.is_initialized():
        return {"error": "MCP Client not initialized", "tools": []}

    from app.mcp.tool_handler import mcp_tool_handler

    categories = mcp_tool_handler.get_tools_by_category()
    all_tools = kubera_mcp_client.get_tool_names()

    return {
        "total_tools": len(all_tools),
        "total_servers": len(categories),
        "categories": categories,
        "all_tools": all_tools,
    }


@app.get("/scheduler/status", tags=["Background Jobs"], summary="Scheduler Status")
async def scheduler_status():
    stats = background_scheduler.get_statistics()

    return {
        "scheduler": {
            "running": stats["running"],
            "total_jobs": stats["total_jobs"],
        },
        "jobs": stats["jobs"],
    }


# ============================================================================
# RUN APP
# ============================================================================

if __name__ == "__main__":

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
