"""Serve the production SPA alongside the unmodified upstream FastAPI app."""

from pathlib import PurePosixPath

from src.main import app
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class Frontend(StaticFiles):
    async def get_response(self, path, scope):
        # Unknown API paths must retain HTTP errors instead of returning HTML.
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            # Vue Router uses extensionless paths. Missing assets stay 404.
            if (
                exc.status_code != 404
                or PurePosixPath(path).suffix
                or path.startswith("assets/")
            ):
                raise
            return await super().get_response("index.html", scope)


# Replace upstream's JSON landing page; existing API and docs routes run first.
app.router.routes[:] = [
    route for route in app.router.routes if getattr(route, "path", None) != "/"
]
app.mount("/", Frontend(directory="/app/frontend", html=True), name="frontend")
