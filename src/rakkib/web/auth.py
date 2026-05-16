"""Token and cookie-backed auth helpers for the local web runtime."""

from __future__ import annotations

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse

from rakkib.secret_utils import compare_digest, token_urlsafe

SESSION_COOKIE_NAME = "rakkib_session"
RECOVERY_COMMAND = "rakkib web --lan"


class AuthManager:
    """Own the in-memory bootstrap token and session cookie state."""

    def __init__(self, *, startup_token: str | None, token_auth_enabled: bool) -> None:
        self._startup_token = startup_token or ""
        self._token_auth_enabled = token_auth_enabled
        self._sessions: dict[str, str] = {}

    @property
    def token_auth_enabled(self) -> bool:
        """Return whether token auth is active for this process."""
        return self._token_auth_enabled

    def authenticate_request(self, request: Request) -> bool:
        """Return True when the request carries a valid session or bearer token."""
        if not self._token_auth_enabled:
            return True

        session_id = request.cookies.get(SESSION_COOKIE_NAME, "")
        if session_id and session_id in self._sessions:
            return True

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            bearer = auth_header.removeprefix("Bearer ").strip()
            return self.validate_token(bearer)

        return False

    def allow_setup_route(self, request: Request) -> bool:
        """Allow setup routes only when already authenticated."""
        return self.authenticate_request(request)

    def validate_token(self, token: str | None) -> bool:
        """Return True when the provided bootstrap token matches this process."""
        if not self._token_auth_enabled:
            return True
        if not token:
            return False
        return compare_digest(token, self._startup_token)

    def issue_session(self) -> tuple[str, str]:
        """Create and remember a new in-memory session id and CSRF token."""
        session_id = token_urlsafe(32)
        csrf_token = token_urlsafe(32)
        self._sessions[session_id] = csrf_token
        return session_id, csrf_token

    def csrf_token_for_request(self, request: Request) -> str | None:
        """Return the CSRF token for the request's active session cookie."""
        session_id = request.cookies.get(SESSION_COOKIE_NAME, "")
        if not session_id:
            return None
        return self._sessions.get(session_id)

    def revoke_session_for_request(self, request: Request) -> None:
        """Forget the active cookie-backed session, if one exists."""
        session_id = request.cookies.get(SESSION_COOKIE_NAME, "")
        if session_id:
            self._sessions.pop(session_id, None)

    def require_csrf(self, request: Request) -> None:
        """Raise a 403 when a cookie-authenticated mutation lacks a valid CSRF token."""
        expected = self.csrf_token_for_request(request)
        if expected is None:
            return

        provided = request.headers.get("x-csrf-token", "")
        if compare_digest(provided, expected):
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid CSRF token.",
        )

    def bootstrap_token(self) -> str | None:
        """Return the active bootstrap token for this process when enabled."""
        if not self._token_auth_enabled:
            return None
        return self._startup_token or None

    def set_session_cookie(self, response: Response, session_id: str) -> None:
        """Persist the session id as an HTTP-only cookie."""
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="strict",
            secure=False,
            path="/",
        )

    def clear_session_cookie(self, response: Response) -> None:
        """Clear the browser session cookie."""
        response.delete_cookie(
            key=SESSION_COOKIE_NAME,
            path="/",
            samesite="strict",
        )

    def require_api_auth(self, request: Request) -> None:
        """Raise a 401 when API auth is missing or invalid."""
        if self.authenticate_request(request):
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Missing or invalid web session. Open the printed setup URL again or run "
                f"`{RECOVERY_COMMAND}` to generate a fresh token."
            ),
        )

    def reject_setup_response(self) -> HTMLResponse:
        """Return an actionable 401 page for unauthenticated setup route requests."""
        body = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Rakkib setup access required</title>
    <style>
      :root {{ color-scheme: dark; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
      body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: #201d1d; color: #fdfcfc; }}
      main {{ width: min(92vw, 720px); padding: 32px; border: 1px solid #646262; border-radius: 4px; background: #302c2c; }}
      p {{ color: #9a9898; line-height: 1.6; }}
      code {{ display: block; margin-top: 20px; padding: 16px; border: 1px solid #646262; background: #201d1d; overflow-x: auto; }}
      a {{ color: #fdfcfc; }}
    </style>
  </head>
  <body>
    <main>
      <h1>Setup access required</h1>
      <p>This setup route needs a valid session cookie or setup token from the current <code>rakkib web</code> process.</p>
      <p>Open the printed URL again, or restart the local web session with:</p>
      <code>{RECOVERY_COMMAND}</code>
      <p><a href=\"/\">Return to the landing page</a></p>
    </main>
  </body>
</html>
"""
        return HTMLResponse(
            body,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"Cache-Control": "no-store"},
        )
