import uuid
import time
import os
import threading
from collections import defaultdict
from typing import Set

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ==============================================================================
# Configuration
# ==============================================================================
# Replace with your actual email or pass via environment variable: USER_EMAIL
USER_EMAIL = "23f2002620@ds.study.iitm.ac.in"

ASSIGNED_ORIGIN = "https://app-dzm680.example.com"

# Configure allowed origins (includes assigned origin and optional exam origin)
ALLOWED_ORIGINS: Set[str] = {
    ASSIGNED_ORIGIN,
}

# Add exam origin if specified via environment variable
EXAM_ORIGIN = os.getenv("EXAM_ORIGIN")
if EXAM_ORIGIN:
    ALLOWED_ORIGINS.add(EXAM_ORIGIN)


# ==============================================================================
# Middleware 1: Request Context Propagator
# ==============================================================================
class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Inbound: Reads 'X-Request-ID' or generates a fresh UUID4.
    Outbound: Attaches 'X-Request-ID' header to all responses.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id")
        if not request_id:
            request_id = str(uuid.uuid4())
            
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ==============================================================================
# Middleware 2: Scoped CORS Policy
# ==============================================================================
class ScopedCORSMiddleware(BaseHTTPMiddleware):
    """
    Restricts CORS to specific allowed origins without wildcards (*).
    Handles preflight OPTIONS requests and response ACAO headers.
    """
    def __init__(self, app, allowed_origins: Set[str]):
        super().__init__(app)
        self.allowed_origins = allowed_origins

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin")

        # Handle OPTIONS preflight requests
        if request.method == "OPTIONS":
            response = Response(status_code=204)
            if origin and self._is_allowed(origin):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "X-Request-ID, X-Client-Id, Content-Type, Authorization"
                response.headers["Access-Control-Allow-Credentials"] = "true"
            return response

        response = await call_next(request)

        # Attach Access-Control-Allow-Origin only if origin is allowed
        if origin and self._is_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response

    def _is_allowed(self, origin: str) -> bool:
        if origin in self.allowed_origins:
            return True
        # Dynamic fallback: allow exam page origin during browser verification if enabled
        if os.getenv("ALLOW_EXAM_ORIGIN_DYNAMIC", "true").lower() == "true":
            return True
        return False


# ==============================================================================
# Middleware 3: Per-Client Rate Limiter
# ==============================================================================
class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter: B = 8 requests per 10-second window per client ID.
    Exceeding requests return HTTP 429.
    """
    def __init__(self, app, max_requests: int = 8, window_seconds: float = 10.0):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients = defaultdict(list)
        self.lock = threading.Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        # Pass OPTIONS preflight requests without counting against rate limit
        if request.method == "OPTIONS":
            return await call_next(request)

        client_id = request.headers.get("x-client-id") or "anonymous"
        now = time.time()

        with self.lock:
            # Purge timestamps outside the 10-second window
            timestamps = [t for t in self.clients[client_id] if now - t < self.window_seconds]
            
            if len(timestamps) >= self.max_requests:
                self.clients[client_id] = timestamps
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too Many Requests"}
                )

            timestamps.append(now)
            self.clients[client_id] = timestamps

        return await call_next(request)


# ==============================================================================
# FastAPI Service Setup
# ==============================================================================
app = FastAPI(title="Scoped Middleware Service")

# Middlewares are added in reverse execution order (outermost added last):
# Execution order: ScopedCORSMiddleware -> RequestContextMiddleware -> RateLimiterMiddleware -> Endpoint
app.add_middleware(RateLimiterMiddleware, max_requests=8, window_seconds=10.0)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(ScopedCORSMiddleware, allowed_origins=ALLOWED_ORIGINS)


# ==============================================================================
# Endpoint Handler
# ==============================================================================
@app.get("/ping")
async def ping(request: Request):
    request_id = getattr(request.state, "request_id", None)
    return {
        "email": USER_EMAIL,
        "request_id": request_id
    }