"""
Exception Handlers
Global exception handling for FastAPI
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import traceback
from datetime import datetime

from app.exceptions.custom_exceptions import KuberaException

logger = logging.getLogger(__name__)


async def kubera_exception_handler(request: Request, exc: KuberaException):
    """
    Handle all Kubera custom exceptions
    """
    logger.error(f"KuberaException: {exc.message} | Details: {exc.details}")
    
    response_data = {
        "success": False,
        "error": {
            "message": exc.message,
            "type": exc.__class__.__name__
        }
    }
    
    if exc.details:
        response_data["error"]["details"] = exc.details
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.error(f"ValidationError: {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "message": "Validation error",
                "type": "ValidationError",
                "details": errors
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handle all other exceptions
    """
    logger.exception(f"Unhandled exception: {str(exc)}")
    
    # Write to file for debugging
    try:
        with open("error_log.txt", "a") as f:
            f.write(f"\n[{datetime.now()}] Unhandled exception: {str(exc)}\n{traceback.format_exc()}\n")
    except Exception as e:
        print(f"Failed to write error log: {e}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "message": "Internal server error",
                "type": "InternalServerError",
                "debug": str(exc)  # Actual error for debugging
            }
        }
    )
