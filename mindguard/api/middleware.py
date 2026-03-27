"""Custom middleware for MindGuard AI API."""

import time
import uuid
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from config.logging_config import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add request ID."""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request details."""
        # Generate request ID if not present
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        
        # Log request
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
        
        # Process request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Log response
            duration = time.time() - start_time
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2)
                }
            )
            
            # Add performance headers
            response.headers["X-Response-Time"] = str(round(duration * 1000, 2))
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2)
                },
                exc_info=True
            )
            raise


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware."""
    
    def __init__(self, app: ASGIApp, allowed_origins: list = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle CORS preflight and headers."""
        origin = request.headers.get("origin")
        
        # Handle preflight
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)
        
        # Add CORS headers
        if origin and (self.allowed_origins == ["*"] or origin in self.allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Request-ID"
            response.headers["Access-Control-Max-Age"] = "3600"
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers."""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        csp = (
            "default-src 'self';"
            "script-src 'self' 'unsafe-inline' 'unsafe-eval';"
            "style-src 'self' 'unsafe-inline';"
            "img-src 'self' data: https:;"
            "font-src 'self';"
            "connect-src 'self' ws: wss:;"
            "frame-ancestors 'none';"
            "base-uri 'self';"
            "form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect metrics for Prometheus."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_count = 0
        self.request_duration_sum = 0
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect metrics."""
        self.request_count += 1
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        self.request_duration_sum += duration
        
        # Store metrics in request state for Prometheus
        request.state.metrics = {
            "request_count": self.request_count,
            "avg_duration_ms": (self.request_duration_sum / self.request_count) * 1000
        }
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle errors gracefully."""
        try:
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Unhandled error: {str(e)}", exc_info=True)
            
            # Return friendly error response
            from fastapi.responses import JSONResponse
            from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
            
            return JSONResponse(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "detail": str(e) if request.app.debug else "An unexpected error occurred",
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            )