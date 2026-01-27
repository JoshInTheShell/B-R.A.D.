# Visual Media Tool (Streamlit)

A lightweight tool that analyzes a script/transcript and suggests **searchable b‑roll/media** terms,
then queries stock providers (Pexels, Pixabay, Unsplash) to surface results you can preview and export.

Built with **Streamlit** + **pure‑Python heuristics** (no heavyweight NLP by default).
Optional: plug in OpenTimelineIO to import cues from your timelines.

---

## ✨ Features (Latest Design)
- **Input**: paste text or upload `.txt` / `.docx` / `.md`. (OTIO import optional)
- **Content Analysis**: RAKE‑style keywords, naive entity & action extraction, basic tone/emotion heuristics.
- **Query Builder**: turns analysis into search-ready queries (topics × actions × emotions).
- **Providers**: Pexels, Pixabay, Unsplash via simple adapters (enable/disable in UI).
- **Results**: inline thumbnails, titles, direct links, attribution notes.
- **Exports (Polish)**:
  - CSV/JSON of selected results (cue sheet)
  - Shot list with query → pick mapping
  - Session save/load as `.vmt.json`
- **Batch Mode (Polish)**: run multiple scenes/blocks at once.
- **OTIO (Optional Polish)**: import text/markers to seed queries if you have `opentimelineio` installed.

---

## Quickstart

```bash
# 1) Create and activate a virtual environment (recommended)
python -m venv .venv && . .venv/bin/activate  # (Windows: .venv\Scripts\activate)

# 2) Install deps
pip install -r requirements.txt
# (Optional) OTIO integration
# pip install opentimelineio

# 3) Set provider API keys (add to .env or your shell):
#   PEXELS_API_KEY=...
#   PIXABAY_API_KEY=...
#   UNSPLASH_ACCESS_KEY=...

# 4) Run
streamlit run app.py
```

### .env
Copy `.env.example` → `.env` and fill keys. Streamlit reloads on save.

---

## Provider Notes

- **Pexels**: https://www.pexels.com/api/ (use `Authorization` header).
- **Pixabay**: https://pixabay.com/api/docs/ (`key` query param).
- **Unsplash**: https://unsplash.com/documentation (`Authorization: Client-ID <key>`).

This app only requests **read‑only** search endpoints and links directly to provider pages for downloads and licenses.

---

## Dev

```bash
make dev        # install deps
make run        # streamlit run app.py
make test       # basic analyzer tests
```

### Structure
```
visual-media-tool/
├─ app.py
├─ requirements.txt
├─ Makefile
├─ .gitignore
├─ .env.example
├─ examples/sample_script.txt
├─ src/vmt/
│  ├─ __init__.py
│  ├─ analyzer.py
│  ├─ search.py
│  ├─ exporters.py
│  ├─ config.py
│  ├─ otio_integration.py      # optional
│  └─ providers/
│     ├─ base.py
│     ├─ pexels.py
│     ├─ pixabay.py
│     └─ unsplash.py
└─ tests/test_analyzer.py
```

---

## License
MIT
