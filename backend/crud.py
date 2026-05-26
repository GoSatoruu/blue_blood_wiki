"""
crud.py — All CRUD operations for wiki articles.
Uses raw aiosqlite for full control over queries.
"""

from datetime import datetime, timezone
from typing import Optional
import mistune

from backend.database import get_db
from backend.models import ArticleCreate, ArticleUpdate, ArticleOut, SearchResult, CategoryInfo

_md = mistune.create_markdown(escape=False, plugins=["table", "strikethrough", "task_lists"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _render_html(content: str) -> str:
    return _md(content)


def _row_to_article(row) -> ArticleOut:
    return ArticleOut(
        id=row["id"],
        slug=row["slug"],
        title=row["title"],
        content=row["content"],
        html_content=row["html_content"],
        tags=row["tags"],
        category=row["category"],
        view_count=row["view_count"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def get_article_by_slug(slug: str, increment_view: bool = False) -> Optional[ArticleOut]:
    """Fetch a single article by its slug. Optionally increment the view counter."""
    db = await get_db()
    try:
        async with db.execute(
            "SELECT * FROM articles WHERE slug = ?", (slug,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        article = _row_to_article(row)
        if increment_view:
            await db.execute(
                "UPDATE articles SET view_count = view_count + 1 WHERE slug = ?", (slug,)
            )
            await db.commit()
        return article
    finally:
        await db.close()


async def get_recent_articles(limit: int = 10) -> list[ArticleOut]:
    """Return the most recently updated articles."""
    db = await get_db()
    try:
        async with db.execute(
            "SELECT * FROM articles ORDER BY updated_at DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
        return [_row_to_article(r) for r in rows]
    finally:
        await db.close()


async def get_all_articles() -> list[ArticleOut]:
    """Return all articles ordered alphabetically by title."""
    db = await get_db()
    try:
        async with db.execute(
            "SELECT * FROM articles ORDER BY title ASC"
        ) as cur:
            rows = await cur.fetchall()
        return [_row_to_article(r) for r in rows]
    finally:
        await db.close()


async def get_categories() -> list[CategoryInfo]:
    """Return all distinct categories with article counts."""
    db = await get_db()
    try:
        async with db.execute(
            """
            SELECT category, COUNT(*) AS article_count
            FROM articles
            GROUP BY category
            ORDER BY article_count DESC
            """
        ) as cur:
            rows = await cur.fetchall()
        return [CategoryInfo(category=r["category"], article_count=r["article_count"]) for r in rows]
    finally:
        await db.close()


async def create_article(data: ArticleCreate) -> ArticleOut:
    """Insert a new article into the database."""
    html = _render_html(data.content)
    now = _now_iso()
    db = await get_db()
    try:
        async with db.execute(
            """
            INSERT INTO articles (slug, title, content, html_content, tags, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (data.slug, data.title, data.content, html, data.tags, data.category, now, now),
        ) as cur:
            article_id = cur.lastrowid
        await db.commit()
        async with db.execute("SELECT * FROM articles WHERE id = ?", (article_id,)) as cur:
            row = await cur.fetchone()
        return _row_to_article(row)
    finally:
        await db.close()


async def update_article(slug: str, data: ArticleUpdate) -> Optional[ArticleOut]:
    """Update an existing article. Returns None if slug not found."""
    db = await get_db()
    try:
        async with db.execute("SELECT * FROM articles WHERE slug = ?", (slug,)) as cur:
            existing = await cur.fetchone()
        if existing is None:
            return None

        new_title = data.title if data.title is not None else existing["title"]
        new_content = data.content if data.content is not None else existing["content"]
        new_tags = data.tags if data.tags is not None else existing["tags"]
        new_category = data.category if data.category is not None else existing["category"]
        new_html = _render_html(new_content)
        now = _now_iso()

        await db.execute(
            """
            UPDATE articles
            SET title = ?, content = ?, html_content = ?, tags = ?, category = ?, updated_at = ?
            WHERE slug = ?
            """,
            (new_title, new_content, new_html, new_tags, new_category, now, slug),
        )
        await db.commit()
        async with db.execute("SELECT * FROM articles WHERE slug = ?", (slug,)) as cur:
            row = await cur.fetchone()
        return _row_to_article(row)
    finally:
        await db.close()


async def search_articles(query: str, limit: int = 20) -> list[SearchResult]:
    """
    Full-text search using FTS5. Falls back to LIKE-based search for safety.
    Returns matched articles with a short content snippet.
    """
    if not query or not query.strip():
        return []

    db = await get_db()
    try:
        safe_query = query.strip().replace('"', '""')
        fts_query = f'"{safe_query}"'
        try:
            async with db.execute(
                """
                SELECT a.slug, a.title, a.tags, a.category, a.content
                FROM articles_fts fts
                JOIN articles a ON a.id = fts.rowid
                WHERE articles_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, limit),
            ) as cur:
                rows = await cur.fetchall()
        except Exception:
            # Fallback: LIKE-based search
            pattern = f"%{query}%"
            async with db.execute(
                """
                SELECT slug, title, tags, category, content FROM articles
                WHERE title LIKE ? OR tags LIKE ? OR content LIKE ?
                ORDER BY updated_at DESC LIMIT ?
                """,
                (pattern, pattern, pattern, limit),
            ) as cur:
                rows = await cur.fetchall()

        results = []
        for r in rows:
            content = r["content"] or ""
            snippet = _make_snippet(content, query)
            results.append(
                SearchResult(
                    slug=r["slug"],
                    title=r["title"],
                    tags=r["tags"],
                    category=r["category"],
                    snippet=snippet,
                )
            )
        return results
    finally:
        await db.close()


def _make_snippet(content: str, query: str, radius: int = 120) -> str:
    """Extract a short context snippet around the first match of query in content."""
    import re
    content_lower = content.lower()
    query_lower = query.lower()
    idx = content_lower.find(query_lower)
    if idx == -1:
        # Return first 120 chars of content stripped of markdown markers
        clean = re.sub(r"[#*_`\[\]>]", "", content)
        return clean[:radius].strip() + ("…" if len(clean) > radius else "")
    start = max(0, idx - radius // 2)
    end = min(len(content), idx + len(query) + radius // 2)
    snippet = content[start:end]
    clean = re.sub(r"[#*_`\[\]>]", "", snippet)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(content) else ""
    return prefix + clean.strip() + suffix
