# Blue Blood Wiki

A self-hosted, community-driven wiki platform for the **Blue Blood** universe — built with FastAPI, SQLite, and Vanilla JS.

---

## 🗂️ Project Structure

```
blue_blood_wiki/
├── app.py                    # FastAPI entry point
├── requirements.txt          # Python dependencies
├── wiki.db                   # SQLite DB (auto-created on first run)
│
├── backend/
│   ├── database.py           # DB connection & schema init
│   ├── models.py             # Pydantic data models
│   ├── crud.py               # CRUD + FTS search operations
│   └── routes/
│       ├── pages.py          # HTML page routes
│       └── api.py            # JSON API routes
│
├── templates/
│   ├── base.html             # Master layout
│   ├── index.html            # Homepage
│   ├── article.html          # Article view
│   ├── edit.html             # Create / Edit form
│   ├── search.html           # Search results
│   ├── category.html         # Category listing
│   ├── 404.html              # Not found page
│   └── 500.html              # Server error page
│
└── static/
    ├── css/wiki.css          # Full stylesheet (dark/light themes)
    └── js/
        ├── theme.js          # Dark/light theme toggle
        ├── search.js         # Live search with keyboard nav
        └── editor.js         # Markdown editor with live preview
```

---

## ⚙️ Installation

### 1. Prerequisites

- Python 3.11 or later
- pip

### 2. Clone / Navigate to the project

```bash
cd blue_blood_wiki
```

### 3. Create a virtual environment (recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Running the Server

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Then open your browser at: **http://localhost:8000**

The SQLite database (`wiki.db`) is created automatically on first startup, pre-seeded with three sample articles:
- *Blue Blood — Overview* (Lore)
- *Kenjaku Voss* (Characters)
- *The First Culling* (History)

---

## 📖 Features

| Feature | Details |
|---------|---------|
| **Homepage** | Recent articles grid, category badges, hero search |
| **Article View** | Rendered Markdown, sidebar with metadata & navigation, tags |
| **Editor** | Split-pane Markdown editor with live preview & toolbar |
| **Search** | FTS5 full-text search + LIKE fallback, live dropdown |
| **Categories** | Browse articles by category |
| **Dark/Light Mode** | Persists across sessions via localStorage |
| **API** | JSON endpoints at `/api/*` (auto-docs at `/api/docs`) |

---

## 🌐 URL Reference

| URL | Description |
|-----|-------------|
| `/` | Homepage |
| `/wiki/<slug>` | View article |
| `/wiki/<slug>/edit` | Edit or create an article |
| `/search?q=<query>` | Full-text search results |
| `/category/<name>` | Browse articles by category |
| `/api/search?q=<query>` | JSON search API |
| `/api/articles` | JSON list of all articles |
| `/api/articles/<slug>` | JSON single article detail |
| `/api/categories` | JSON category list with counts |
| `/api/docs` | Interactive OpenAPI documentation |

---

## 🛠️ Development Tips

- **Add an article**: Navigate to `/wiki/any-slug/edit` to create a new page.
- **Edit sample articles**: Visit `/wiki/kenjaku-voss/edit` to experiment.
- **Inspect the database**: `sqlite3 wiki.db ".tables"` or use any SQLite viewer.
- **API playground**: Visit `http://localhost:8000/api/docs` for Swagger UI.

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server |
| `jinja2` | HTML templating |
| `aiosqlite` | Async SQLite access |
| `mistune` | Markdown → HTML rendering |
| `python-multipart` | Form data parsing |
| `python-slugify` | URL-safe slug generation |

---

## 🔮 Roadmap (Phase 2+)

- User authentication & per-user edit history
- Article revision history & diff viewer
- Image uploads with local storage
- Advanced Markdown extensions (footnotes, mermaid diagrams)
- Full-text indexing with ranking improvements
- RSS feed for recent changes