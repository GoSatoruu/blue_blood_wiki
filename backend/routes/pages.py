"""
routes/pages.py — HTML page routes for Blue Blood Wiki.

Routes:
  GET  /                        → Homepage
  GET  /wiki/{slug}             → Article view (or 404)
  GET  /wiki/{slug}/edit        → Edit/Create form
  POST /wiki/{slug}/edit        → Save article, redirect to view
  GET  /search                  → Search results page
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from slugify import slugify as _slugify
from typing import Optional

from backend import crud
from backend.models import ArticleCreate, ArticleUpdate

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _format_date(iso_str: str) -> str:
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%B %d, %Y")
    except Exception:
        return iso_str


templates.env.filters["format_date"] = _format_date


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    recent_articles = await crud.get_recent_articles(limit=12)
    categories = await crud.get_categories()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "recent_articles": recent_articles,
            "categories": categories,
            "page_title": "Blue Blood Wiki — Home",
        },
    )


@router.get("/wiki/{slug}", response_class=HTMLResponse)
async def article_view(request: Request, slug: str):
    article = await crud.get_article_by_slug(slug, increment_view=True)
    if article is None:
        return templates.TemplateResponse(
            "404.html",
            {
                "request": request,
                "slug": slug,
                "page_title": "Page Not Found — Blue Blood Wiki",
            },
            status_code=404,
        )
    tag_list = [t.strip() for t in article.tags.split(",") if t.strip()]
    recent = await crud.get_recent_articles(limit=8)
    categories = await crud.get_categories()
    return templates.TemplateResponse(
        "article.html",
        {
            "request": request,
            "article": article,
            "tag_list": tag_list,
            "recent_articles": recent,
            "categories": categories,
            "page_title": f"{article.title} — Blue Blood Wiki",
        },
    )


@router.get("/wiki/{slug}/edit", response_class=HTMLResponse)
async def edit_article_form(request: Request, slug: str):
    article = await crud.get_article_by_slug(slug)
    categories = await crud.get_categories()
    return templates.TemplateResponse(
        "edit.html",
        {
            "request": request,
            "article": article,
            "slug": slug,
            "categories": categories,
            "is_new": article is None,
            "page_title": (
                f"Edit: {article.title} — Blue Blood Wiki"
                if article
                else f"Create: {slug} — Blue Blood Wiki"
            ),
        },
    )


@router.post("/wiki/{slug}/edit", response_class=HTMLResponse)
async def save_article(
    request: Request,
    slug: str,
    title: str = Form(...),
    content: str = Form(default=""),
    tags: str = Form(default=""),
    category: str = Form(default="General"),
    new_slug: str = Form(default=""),
):
    # Use submitted new_slug if provided and valid, otherwise keep existing
    final_slug = new_slug.strip() if new_slug.strip() else slug
    if not final_slug:
        final_slug = _slugify(title, separator="-")

    existing = await crud.get_article_by_slug(slug)

    if existing is None:
        # Create new article
        data = ArticleCreate(
            title=title,
            slug=final_slug,
            content=content,
            tags=tags,
            category=category,
        )
        await crud.create_article(data)
    else:
        # Update existing article
        data = ArticleUpdate(
            title=title,
            content=content,
            tags=tags,
            category=category,
        )
        await crud.update_article(slug, data)
        # Handle slug change: if the slug was changed, the URL changes
        # For Phase 1 we keep the same slug to avoid dead links
        final_slug = slug

    return RedirectResponse(url=f"/wiki/{final_slug}", status_code=303)


@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = ""):
    results = []
    if q.strip():
        results = await crud.search_articles(q.strip())
    categories = await crud.get_categories()
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "query": q,
            "results": results,
            "categories": categories,
            "page_title": f'Search: "{q}" — Blue Blood Wiki' if q else "Search — Blue Blood Wiki",
        },
    )


@router.get("/category/{category_name}", response_class=HTMLResponse)
async def category_page(request: Request, category_name: str):
    import aiosqlite
    from backend.database import get_db

    db = await get_db()
    try:
        async with db.execute(
            "SELECT * FROM articles WHERE category = ? ORDER BY title ASC",
            (category_name,),
        ) as cur:
            rows = await cur.fetchall()
    finally:
        await db.close()

    from backend.crud import _row_to_article
    articles = [_row_to_article(r) for r in rows]
    categories = await crud.get_categories()

    return templates.TemplateResponse(
        "category.html",
        {
            "request": request,
            "category_name": category_name,
            "articles": articles,
            "categories": categories,
            "page_title": f"{category_name} — Blue Blood Wiki",
        },
    )
