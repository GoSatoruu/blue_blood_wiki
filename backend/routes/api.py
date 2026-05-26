"""
routes/api.py — JSON API endpoints for Blue Blood Wiki.

Routes:
  GET /api/search?q=...     → Full-text search results as JSON
  GET /api/articles         → All articles (abbreviated) as JSON
  GET /api/articles/{slug}  → Single article as JSON
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse

from backend import crud
from backend.models import SearchResult, ArticleOut

router = APIRouter(prefix="/api")


@router.get("/search")
async def api_search(q: str = Query(default="", description="Search query string")):
    """Return a JSON array of articles matching the query."""
    if not q.strip():
        return JSONResponse(content=[])
    results = await crud.search_articles(q.strip(), limit=10)
    return JSONResponse(
        content=[
            {
                "slug": r.slug,
                "title": r.title,
                "tags": r.tags,
                "category": r.category,
                "snippet": r.snippet,
                "url": f"/wiki/{r.slug}",
            }
            for r in results
        ]
    )


@router.get("/articles")
async def api_articles():
    """Return all articles (abbreviated fields) as a JSON array."""
    articles = await crud.get_all_articles()
    return JSONResponse(
        content=[
            {
                "slug": a.slug,
                "title": a.title,
                "tags": a.tags,
                "category": a.category,
                "view_count": a.view_count,
                "updated_at": a.updated_at,
                "url": f"/wiki/{a.slug}",
            }
            for a in articles
        ]
    )


@router.get("/articles/{slug}")
async def api_article_detail(slug: str):
    """Return the full article data as JSON."""
    article = await crud.get_article_by_slug(slug)
    if article is None:
        raise HTTPException(status_code=404, detail=f"Article '{slug}' not found")
    return JSONResponse(
        content={
            "id": article.id,
            "slug": article.slug,
            "title": article.title,
            "content": article.content,
            "html_content": article.html_content,
            "tags": article.tags,
            "category": article.category,
            "view_count": article.view_count,
            "created_at": article.created_at,
            "updated_at": article.updated_at,
        }
    )


@router.get("/categories")
async def api_categories():
    """Return all categories with article counts."""
    categories = await crud.get_categories()
    return JSONResponse(
        content=[
            {"category": c.category, "article_count": c.article_count}
            for c in categories
        ]
    )
