"""ASGI app factory for the Rakkib browser UI."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from .api import build_api_router
from .auth import AuthManager
from .models import WebRuntimeConfig
from .run import WebRunManager
from .static import packaged_index_path, resolve_packaged_file


def create_app(config: WebRuntimeConfig) -> FastAPI:
    """Create the FastAPI application for `rakkib web`."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, title="Rakkib Web")
    auth = AuthManager(
        startup_token=config.startup_token,
        token_auth_enabled=config.token_auth_enabled,
    )
    run_manager = WebRunManager(config.repo_dir)

    app.state.web_config = config
    app.state.auth = auth
    app.state.run_manager = run_manager
    app.include_router(build_api_router(auth, config, run_manager), prefix="/api")

    @app.get("/{requested_path:path}", include_in_schema=False)
    def static_entry(request: Request, requested_path: str = ""):
        normalized = requested_path.strip("/")

        if normalized == ".well-known/appspecific/com.chrome.devtools.json":
            return JSONResponse({})

        if normalized:
            file_path = resolve_packaged_file(normalized)
            if file_path is not None:
                return FileResponse(file_path)

        if not normalized:
            return FileResponse(packaged_index_path())

        if normalized == "setup" or normalized.startswith("setup/"):
            if not auth.allow_setup_route(request):
                return auth.reject_setup_response()
            return FileResponse(packaged_index_path(), headers={"Cache-Control": "no-store"})

        raise HTTPException(status_code=404, detail="Not found")

    return app
