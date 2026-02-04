import os, io, json, base64
from pathlib import Path
from typing import List, Dict
from dataclasses import asdict

import streamlit as st
from dotenv import load_dotenv

from src.vmt.analyzer import analyze_text, build_queries
from src.vmt.search import MediaSearcher
from src.vmt.exporters import export_csv, export_json, export_shotlist
from src.vmt.config import Settings

load_dotenv()

st.set_page_config(page_title="Visual Media Tool", page_icon="🎬", layout="wide")

st.title("🎬 Visual Media Tool")
st.caption("Analyze a script/transcript → build queries → fetch stock media → export cue sheets.")

with st.expander("Provider API Keys (from environment)", expanded=False):
    st.write("Pexels:`PEXELS_API_KEY`, Pixabay:`PIXABAY_API_KEY`, Unsplash:`UNSPLASH_ACCESS_KEY`")
    st.code("\n".join([
        f"PEXELS_API_KEY={os.getenv('PEXELS_API_KEY', '')}",
        f"PIXABAY_API_KEY={os.getenv('PIXABAY_API_KEY', '')}",
        f"UNSPLASH_ACCESS_KEY={os.getenv('UNSPLASH_ACCESS_KEY', '')}",
    ]), language="bash")

def get_search_url(source, media_type):
    if source == "pixabay":
        return (
            "https://pixabay.com/api/videos/"
            if media_type == "video"
            else "https://pixabay.com/api/"
        )

    if source == "pexels":
        return (
            "https://api.pexels.com/videos/search"
            if media_type == "video"
            else "https://api.pexels.com/v1/search"
        )

    raise ValueError("Unsupported source")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    enable_pexels = st.checkbox("Enable Pexels", True)
    enable_pixabay = st.checkbox("Enable Pixabay", True)
    enable_unsplash = st.checkbox("Enable Unsplash", True)
    per_query = st.slider("Results per provider", 4, 30, 12, 1)
    st.markdown("---")
    st.subheader("Exports")
    export_base = st.text_input("Export base filename", value="vmt_session")
    media_type = st.radio(
    "Media type",
    ["Photo", "Video"],
    horizontal=True
)
    media_type = media_type.lower()  # "photo" or "video"

# Input
tab1, tab2, tab3 = st.tabs(["Paste / Upload", "Batch Mode", "Load Session"])

def read_uploaded_text(upload) -> str:
    name = upload.name.lower()
    data = upload.read()
    if name.endswith(".txt") or name.endswith(".md") or name.endswith(".srt"):
        return data.decode("utf-8", errors="ignore")
    if name.endswith(".docx"):
        try:
            import docx  # python-docx
        except Exception:
            st.error("Install `python-docx` to read .docx files: pip install python-docx")
            return ""
        doc = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    return data.decode("utf-8", errors="ignore")

with tab1:
    st.subheader("Paste text or upload a file")
    text = st.text_area("Script / Transcript", height=240, placeholder="Paste your scene or transcript here...")
    up = st.file_uploader("Upload .txt / .md / .docx (optional)", type=["txt","md","docx","srt"])    
    if up is not None and not text.strip():
        text = read_uploaded_text(up)

    otio_path = st.text_input("(Optional) OTIO file path to import cues (requires opentimelineio)", value="")

    if st.button("Analyze", type="primary"):
        if not text.strip() and not otio_path.strip():
            st.warning("Please provide text or an OTIO path.")
        else:
            if otio_path.strip():
                try:
                    from src.vmt.otio_integration import extract_cues
                    cues = extract_cues(otio_path.strip())
                    cues_text = "\n".join([f"{c.label} {(' - '+c.note) if c.note else ''}" for c in cues])
                    text = text + "\n" + cues_text
                    st.info(f"Imported {len(cues)} cues from OTIO.")
                except Exception as e:
                    st.error(str(e))

            analysis = analyze_text(text)
            st.success("Analyzed! Edit the auto-built queries below or add your own.")

            key_cols = st.columns(3)
            with key_cols[0]:
                st.write("**Top Keywords**")
                st.write(", ".join(k for k,_ in analysis.keywords[:10]) or "—")
            with key_cols[1]:
                st.write("**Entities**")
                st.write(", ".join(analysis.entities[:10]) or "—")
            with key_cols[2]:
                st.write("**Actions/Emotions**")
                st.write(", ".join(analysis.actions[:8] + analysis.emotions[:4]) or "—")

            queries = st.multiselect("Queries",build_queries(analysis),default=build_queries(analysis))
            st.session_state["vmt_queries"] = queries
            st.session_state["vmt_text"] = text

with tab2:
    st.subheader("Batch Mode (one block per line)")
    batch_text = st.text_area("Blocks", height=200, placeholder="One scene or beat per line...")
    if st.button("Analyze Batch"):
        blocks = [b.strip() for b in batch_text.splitlines() if b.strip()]
        all_queries = []
        for b in blocks:
            a = analyze_text(b)
            all_queries.extend(build_queries(a, limit=6))
        # de-dup keep order
        seen = set(); dedup = []
        for q in all_queries:
            if q not in seen:
                seen.add(q); dedup.append(q)
        st.session_state["vmt_queries"] = dedup
        st.success(f"Generated {len(dedup)} queries from {len(blocks)} blocks.")

with tab3:
    st.subheader("Load a saved session (.vmt.json)")
    sess_up = st.file_uploader("Upload session", type=["json"])    
    if sess_up is not None:
        try:
            obj = json.load(sess_up)
            st.session_state["vmt_queries"] = obj.get("queries", [])
            st.session_state["vmt_text"] = obj.get("text", "")
            st.success("Session loaded.")
        except Exception as e:
            st.error(str(e))

# Search
if "vmt_queries" in st.session_state and st.session_state["vmt_queries"]:
    st.markdown("---")
    st.header("Search & Pick")

    settings = Settings.from_env()
    searcher = MediaSearcher(settings, enabled={
        "Pexels": enable_pexels,
        "Pixabay": enable_pixabay,
        "Unsplash": enable_unsplash,
    })

    queries: List[str] = st.session_state["vmt_queries"]
    chosen: Dict[str, Dict] = {}

    for q in queries:
        st.subheader(q)
        results = searcher.search_all(q, limit=per_query)
        if not results:
            st.info("No results or providers disabled.")
            continue
        cols = st.columns(4)
        for i, r in enumerate(results):
            c = cols[i % 4]
            with c:
                if r.thumb:
                    st.image(r.thumb, use_container_width=True)
                st.caption(f"{r.title}\n\n[{r.provider}] • {r.author or '—'}")
                st.link_button("Open", r.url, use_container_width=True)
                if st.button("Select", key=f"sel-{q}-{i}", use_container_width=True):
                    chosen[q] = {
                        "query": q,
                        "title": r.title, "provider": r.provider,
                        "url": r.url, "thumb": r.thumb,
                        "author": r.author, "license": r.license,
                    }
        st.write("")  # spacing

    st.markdown("---")
    st.subheader("Export")
    colA, colB, colC, colD = st.columns(4)
    session = {
        "text": st.session_state.get("vmt_text", ""),
        "queries": queries,
        "selected": chosen,
    }
    sess_json = json.dumps(session, ensure_ascii=False, indent=2)
    b64 = base64.b64encode(sess_json.encode()).decode()
    colA.download_button("⬇️ Save Session (.vmt.json)", data=sess_json, file_name=f"{export_base}.vmt.json")

    rows = [dict(query=q, **v) for q,v in chosen.items()]
    csv_path = Path(f"{export_base}.csv").as_posix()
    json_path = Path(f"{export_base}.json").as_posix()
    colB.download_button("⬇️ Cue Sheet CSV", data="".encode("utf-8"), file_name=csv_path)
    colC.download_button("⬇️ Results JSON", data=json.dumps(rows, ensure_ascii=False, indent=2), file_name=json_path)
    # Shotlist reuses CSV exporter
    colD.download_button("⬇️ Shotlist CSV", data="".encode("utf-8"), file_name=f"{export_base}.shotlist.csv")
else:
    st.info("Start by analyzing text to generate queries.")
