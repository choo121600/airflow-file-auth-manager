"""FastAPI endpoints for file-based authentication."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from airflow.configuration import conf

from airflow_file_auth_manager.password import verify_password

if TYPE_CHECKING:
    from airflow_file_auth_manager.file_auth_manager import FileAuthManager

logger = logging.getLogger(__name__)

# Template and static file paths
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"


def create_auth_app(auth_manager: FileAuthManager) -> FastAPI:
    """Create FastAPI app with authentication endpoints.

    Args:
        auth_manager: The FileAuthManager instance.

    Returns:
        FastAPI app with /login, /token, and /logout endpoints.
    """
    app = FastAPI(
        title="File Auth Manager",
        description="YAML file-based authentication for Apache Airflow",
    )

    # Setup Jinja2 templates
    jinja_env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )

    # Mount static files if directory exists
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Get JWT expiration from config
    jwt_expiration = conf.getint("api_auth", "jwt_expiration_seconds", fallback=36000)

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, next: str | None = None, error: str | None = None) -> HTMLResponse:
        """Render the login page."""
        template = jinja_env.get_template("login.html")
        html = template.render(
            next_url=next or "/",
            error=error,
        )
        return HTMLResponse(content=html)

    @app.post("/token")
    async def create_token(
        request: Request,
        response: Response,
    ) -> Response:
        """Authenticate user and create JWT token.

        Supports both form submission (browser) and JSON API requests.

        Security features:
        - Browser sessions: HttpOnly cookies (protected from XSS)
        - API clients: Bearer tokens in response body (use Authorization header)
        """
        # Handle request based on content type
        content_type = request.headers.get("content-type", "")
        is_form_submission = "application/x-www-form-urlencoded" in content_type
        username: str | None = None
        password: str | None = None
        form_data = None

        if "application/json" in content_type:
            try:
                body = await request.json()
                username = body.get("username")
                password = body.get("password")
            except Exception:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid JSON body"},
                )
        elif is_form_submission:
            form_data = await request.form()
            username = form_data.get("username")
            password = form_data.get("password")

        # Validate input
        if not username or not password:
            logger.warning("AUDIT: Login attempt with missing credentials")
            if is_form_submission:
                return RedirectResponse(
                    url="/auth/login?error=Username+and+password+required",
                    status_code=303,
                )
            return JSONResponse(
                status_code=400,
                content={"error": "Username and password required"},
            )

        # Authenticate user
        user = auth_manager.user_store.authenticate(username, password)
        if not user:
            logger.warning("AUDIT: Failed login attempt for user: %s (IP: %s)",
                          username, request.client.host if request.client else "unknown")
            if is_form_submission:
                return RedirectResponse(
                    url="/auth/login?error=Invalid+username+or+password",
                    status_code=303,
                )
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid username or password"},
            )

        # Create JWT token using auth manager's method
        token = auth_manager.generate_jwt(user, expiration_time_in_seconds=jwt_expiration)

        logger.info("AUDIT: User logged in: %s (IP: %s)",
                   username, request.client.host if request.client else "unknown")

        # Form submission - set HttpOnly cookie and redirect
        if is_form_submission:
            # form_data was already read above
            next_url = form_data.get("next", "/") if form_data else "/"

            # Detect if using HTTPS
            is_secure = (
                request.url.scheme == "https"
                or request.headers.get("x-forwarded-proto") == "https"
            )

            redirect_response = RedirectResponse(url=str(next_url), status_code=303)
            redirect_response.set_cookie(
                key="airflow_jwt",
                value=token,
                max_age=jwt_expiration,
                httponly=True,  # Protect from XSS attacks
                secure=is_secure,
                samesite="lax",
            )
            return redirect_response

        # JSON API - return token in response body
        # Client should use this token in Authorization header: "Bearer <token>"
        return JSONResponse(
            content={
                "access_token": token,
                "token_type": "Bearer",
                "expires_in": jwt_expiration,
            }
        )

    @app.get("/logout")
    async def logout(request: Request) -> RedirectResponse:
        """Log out user by clearing JWT cookie."""
        logger.info("AUDIT: User logged out (IP: %s)",
                   request.client.host if request.client else "unknown")

        redirect_response = RedirectResponse(url="/auth/login", status_code=303)
        redirect_response.delete_cookie(key="airflow_jwt")
        return redirect_response

    return app
