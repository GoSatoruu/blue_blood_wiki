"""
app.py — FastAPI application factory and entry point for Blue Blood Wiki.

Run with:
    uvicorn app:app --reload --host 0.0.0.0 --port 8000
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.database import init_db
from backend.routes.pages import router as pages_router
from backend.routes.api import router as api_router

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database and seed sample data on startup."""
    await init_db()
    yield


app = FastAPI(
    title="Blue Blood Wiki",
    description="A self-hosted fandom wiki platform for the Blue Blood universe.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static",
)

# Register routers
app.include_router(pages_router)
app.include_router(api_router)


# Global exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
    return templates.TemplateResponse(
        "404.html",
        {
            "request": request,
            "slug": "",
            "page_title": "Page Not Found — Blue Blood Wiki",
        },
        status_code=404,
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
    return templates.TemplateResponse(
        "500.html",
        {
            "request": request,
            "page_title": "Server Error — Blue Blood Wiki",
        },
        status_code=500,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
