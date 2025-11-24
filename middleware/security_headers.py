from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        fe = settings.FRONTEND_ORIGIN
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            f"connect-src 'self' {fe}; "
            "frame-ancestors 'none';"
        )
        if settings.HSTS_ENABLED:
            response.headers[
                "Strict-Transport-Security"
            ] = "max-age=63072000; includeSubDomains; preload"
        return response

