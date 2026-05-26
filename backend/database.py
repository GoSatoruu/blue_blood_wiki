"""
database.py — Async SQLite database connection, schema initialization, and
lifecycle helpers for Blue Blood Wiki.
"""

import aiosqlite
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wiki.db")


async def get_db() -> aiosqlite.Connection:
    """Open and return a configured aiosqlite connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA foreign_keys=ON;")
    return db


async def init_db() -> None:
    """Create all required tables if they do not already exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                slug         TEXT    NOT NULL UNIQUE,
                title        TEXT    NOT NULL,
                content      TEXT    NOT NULL DEFAULT '',
                html_content TEXT    NOT NULL DEFAULT '',
                tags         TEXT    NOT NULL DEFAULT '',
                category     TEXT    NOT NULL DEFAULT 'General',
                view_count   INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT    NOT NULL,
                updated_at   TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_articles_slug     ON articles(slug);
            CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
            CREATE INDEX IF NOT EXISTS idx_articles_updated  ON articles(updated_at DESC);

            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                slug,
                title,
                tags,
                content,
                content='articles',
                content_rowid='id'
            );

            CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
                INSERT INTO articles_fts(rowid, slug, title, tags, content)
                VALUES (new.id, new.slug, new.title, new.tags, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, slug, title, tags, content)
                VALUES ('delete', old.id, old.slug, old.title, old.tags, old.content);
                INSERT INTO articles_fts(rowid, slug, title, tags, content)
                VALUES (new.id, new.slug, new.title, new.tags, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, slug, title, tags, content)
                VALUES ('delete', old.id, old.slug, old.title, old.tags, old.content);
            END;
            """
        )
        await db.commit()
        await _seed_sample_data(db)


async def _seed_sample_data(db: aiosqlite.Connection) -> None:
    """Insert sample articles on first run if the table is empty."""
    import mistune

    async with db.execute("SELECT COUNT(*) AS cnt FROM articles") as cur:
        row = await cur.fetchone()
        if row["cnt"] > 0:
            return

    renderer = mistune.create_markdown(escape=False)
    now = datetime.now(timezone.utc).isoformat()

    samples = [
        {
            "slug": "blue-blood-overview",
            "title": "Blue Blood — Overview",
            "content": (
                "# Blue Blood — Overview\n\n"
                "**Blue Blood** is a supernatural thriller manga series that explores the hidden world of "
                "noble vampiric clans clashing with mortal hunters in a grimdark urban fantasy setting.\n\n"
                "## Setting\n\n"
                "The story takes place in the fictional metropolis of **Sanguinis City**, a sprawling coastal "
                "urban centre where vampiric aristocracy secretly controls the political and financial elite. "
                "Beneath glittering skyscrapers lie ancient catacombs where blood rites are still performed.\n\n"
                "## Themes\n\n"
                "- Identity and inheritance\n"
                "- Power corrupts\n"
                "- Loyalty vs. survival\n"
                "- The price of immortality\n\n"
                "## Publication\n\n"
                "First serialised in **Midnight Ink Monthly**, the series spans three story arcs across twelve volumes.\n"
            ),
            "tags": "overview,lore,setting",
            "category": "Lore",
        },
        {
            "slug": "kenjaku-voss",
            "title": "Kenjaku Voss",
            "content": (
                "# Kenjaku Voss\n\n"
                "**Kenjaku Voss** is the primary antagonist of the Blue Blood series. An ancient vampire lord "
                "of the Voss bloodline, he has survived for over eight centuries by periodically transferring "
                "his consciousness into new host bodies.\n\n"
                "## Abilities\n\n"
                "| Ability | Description |\n"
                "|---------|-------------|\n"
                "| Soul Transference | Kenjaku can displace a host's consciousness and inhabit their body |\n"
                "| Blood Sight | He perceives the world through the blood of those he has fed upon |\n"
                "| Ancestral Memory | Access to centuries of absorbed memories and skills |\n\n"
                "## History\n\n"
                "Born mortal in 13th-century Eastern Europe, Kenjaku was turned during the First Culling — "
                "a genocidal purge of mortal mages by the Vampire High Council. Rather than submit, he devoured "
                "his sire and seized their power.\n\n"
                "## Personality\n\n"
                "Coldly intellectual and patient to a fault, Kenjaku views mortal lives as experiments. "
                "He maintains a facade of genteel aristocracy while engineering catastrophic events for amusement.\n"
            ),
            "tags": "character,antagonist,vampire,voss bloodline",
            "category": "Characters",
        },
        {
            "slug": "the-first-culling",
            "title": "The First Culling",
            "content": (
                "# The First Culling\n\n"
                "The **First Culling** (also known as the *Sanguine Purge*) was a coordinated genocide "
                "carried out by the Vampire High Council in 1247 CE, targeting mortal mage-hunters and "
                "rogue vampires who refused to submit to Council authority.\n\n"
                "## Cause\n\n"
                "Rising tensions between mortal mage-hunter guilds and the newly unified Vampire Council "
                "culminated in the Sacking of Varek's Throne — an attack on the Council's seat of power.\n\n"
                "## Events\n\n"
                "Over seven nights, Council enforcers systematically eliminated 47 mage-hunter strongholds "
                "across three continents. Estimated death toll: **~12,000 mortals and 200 rogue vampires**.\n\n"
                "## Legacy\n\n"
                "The First Culling established the Council's supremacy but also sowed the seeds of the "
                "modern Hunter-Vampire cold war. Survivor accounts form the basis of the *Hunter's Codex*, "
                "still used by present-day hunter guilds.\n\n"
                "> *\"They wanted compliance. We gave them war.\"* — Margrave Elsin, survivor\n"
            ),
            "tags": "history,events,vampire council,hunters",
            "category": "History",
        },
    ]

    for s in samples:
        html = renderer(s["content"])
        await db.execute(
            """
            INSERT INTO articles (slug, title, content, html_content, tags, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (s["slug"], s["title"], s["content"], html, s["tags"], s["category"], now, now),
        )
    await db.commit()
