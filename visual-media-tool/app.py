import os, io, json, base64
from pathlib import Path
from typing import List, Dict
from dataclasses import asdict

import streamlit as st
from dotenv import load_dotenv

from src.vmt.analyzer import analyze_text as analyze_text_basic, build_queries
from src.vmt.search import MediaSearcher
from src.vmt.exporters import export_csv, export_json, export_shotlist
from src.vmt.config import Settings

# Try to import Gemini analyzer
try:
    from src.vmt.analyzer_gemini import analyze_text_with_gemini, test_gemini_connection
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    analyze_text_with_gemini = None
    test_gemini_connection = None

load_dotenv()

st.set_page_config(page_title="Visual Media Tool", page_icon="🎬", layout="wide")

st.title("🎬 Visual Media Tool")
st.caption("Analyze a script/transcript → build queries → fetch stock media → export cue sheets.")

with st.expander("Provider API Keys (from environment)", expanded=False):
    st.write("**Stock Media Providers:**")
    st.write("Pexels:`PEXELS_API_KEY`, Pixabay:`PIXABAY_API_KEY`, Unsplash:`UNSPLASH_ACCESS_KEY`")
    st.code("\n".join([
        f"PEXELS_API_KEY={os.getenv('PEXELS_API_KEY', '(not set)')}",
        f"PIXABAY_API_KEY={os.getenv('PIXABAY_API_KEY', '(not set)')}",
        f"UNSPLASH_ACCESS_KEY={os.getenv('UNSPLASH_ACCESS_KEY', '(not set)')}",
    ]), language="bash")
    
    st.write("**AI Analysis (Optional):**")
    st.write("Google Gemini:`GOOGLE_API_KEY` - Get free key at https://makersuite.google.com/app/apikey")
    gemini_key = os.getenv('GOOGLE_API_KEY', '(not set)')
    st.code(f"GOOGLE_API_KEY={gemini_key}", language="bash")
    
    if GEMINI_AVAILABLE and gemini_key != '(not set)':
        if test_gemini_connection():
            st.success("✅ Gemini AI connected and working!")
        else:
            st.error("❌ Gemini API key set but connection failed")


# Sidebar controls
with st.sidebar:
    st.header("Settings")

        # AI Analysis toggle
    st.subheader("🤖 AI Analysis")
    use_ai = False
    if GEMINI_AVAILABLE and os.getenv('GOOGLE_API_KEY'):
        use_ai = st.checkbox(
            "Use Gemini AI for analysis",
            value=True,
            help="Uses Google Gemini for better keyword extraction (free tier: 15/min, 1500/day)"
        )
        if use_ai:
            st.info("💡 AI will generate better, more visual search terms")
    elif GEMINI_AVAILABLE:
        st.warning("⚠️ Add GOOGLE_API_KEY to .env to enable AI")
        st.caption("[Get free key](https://makersuite.google.com/app/apikey)")
    else:
        st.warning("⚠️ Install google-generativeai to enable AI")
    
    st.markdown("---")
    
    # Media type selection
    media_type = st.radio(
        "Media type",
        ["Photo", "Video"],
        horizontal=True,
        help="Choose whether to search for photos or videos"
    )
    media_type = media_type.lower()  # "photo" or "video"
    
    st.markdown("---")
    
    # Provider toggles
    enable_pexels = st.checkbox("Enable Pexels", True, help="Supports both photos and videos")
    enable_pixabay = st.checkbox("Enable Pixabay", True, help="Supports both photos and videos")
    enable_unsplash = st.checkbox("Enable Unsplash", True, help="Photos only (no video API)")
    
    # Show warning if Unsplash is enabled for video
    if media_type == "video" and enable_unsplash:
        st.warning("⚠️ Unsplash doesn't support videos, it will be skipped")
    
    per_query = st.slider("Results per provider", 4, 30, 12, 1)
    
    st.markdown("---")
    st.subheader("Exports")
    export_base = st.text_input("Export base filename", value="vmt_session")

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
        
    # Add a clear button
    if "vmt_queries" in st.session_state:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🗑️ Clear Results", help="Clear previous analysis"):
                st.session_state.pop("vmt_queries", None)
                st.session_state.pop("vmt_text", None)
                st.session_state.pop("vmt_analyzer", None)
                st.session_state.pop("vmt_chosen", None)
                st.rerun()
    
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

            # Choose analyzer based on AI toggle
            analyzer_used = "basic"
            with st.spinner("Analyzing script..." if not use_ai else "🤖 AI analyzing script..."):
                if use_ai and GEMINI_AVAILABLE and os.getenv('GOOGLE_API_KEY'):
                    try:
                        analysis = analyze_text_with_gemini(text)
                        st.success("✅ AI Analysis complete! Edit the auto-built queries below or add your own.")
                    except Exception as e:
                        st.warning(f"AI analysis failed ({str(e)}), falling back to basic analysis")
                        analysis = analyze_text_basic(text)
                        analyzer_used = "basic (AI failed)"

                else:
                    analysis = analyze_text_basic(text)
                                        analyzer_used = "basic"
            
            st.info(f"🔍 Analyzer used: **{analyzer_used}**")

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
                        st.session_state["vmt_analyzer"] = analyzer_used

with tab2:
    st.subheader("Batch Mode (one block per line)")
    batch_text = st.text_area("Blocks", height=200, placeholder="One scene or beat per line...")
    if st.button("Analyze Batch"):
        blocks = [b.strip() for b in batch_text.splitlines() if b.strip()]
        all_queries = []
        
        with st.spinner(f"Analyzing {len(blocks)} blocks..."):
            for b in blocks:
                if use_ai and GEMINI_AVAILABLE and os.getenv('GOOGLE_API_KEY'):
                    try:
                        a = analyze_text_with_gemini(b)
                    except Exception:
                        a = analyze_text_basic(b)
                else:
                    a = analyze_text_basic(b)
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
    
    # Show which analyzer was used for these results
    analyzer_info = st.session_state.get("vmt_analyzer", "unknown")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header(f"Search & Pick ({media_type.title()}s)")
    with col2:
        st.caption(f"Analyzed with: **{analyzer_info}**")
    st.header(f"Search & Pick ({media_type.title()}s)")

    settings = Settings.from_env()
    searcher = MediaSearcher(settings, enabled={
        "Pexels": enable_pexels,
        "Pixabay": enable_pixabay,
        "Unsplash": enable_unsplash,
    })

    queries: List[str] = st.session_state["vmt_queries"]
    chosen: Dict[str, Dict] = st.session_state.get("vmt_chosen", {})

    for q in queries:
        st.subheader(q)
        
        # Pass media_type to the search
        results = searcher.search_all(q, limit=per_query, media_type=media_type)
        
        if not results:
            st.info("No results found or all providers disabled.")
            continue
        
        # Filter out error results for display
        valid_results = [r for r in results if not r.extra.get("error")]
        error_results = [r for r in results if r.extra.get("error")]
        
        if error_results:
            for err in error_results:
                st.error(f"❌ {err.title}")
        
        if not valid_results:
            st.warning("No valid results after errors.")
            continue
            
        cols = st.columns(4)
        for i, r in enumerate(valid_results):
            c = cols[i % 4]
            with c:
                 # Display thumbnail
                if r.thumb:
                    st.image(r.thumb, use_container_width=True)
                else:
                    st.info("No preview available")
                
                # Show title and metadata
                caption_parts = [f"**{r.title[:50]}**"]
                caption_parts.append(f"[{r.provider}]")
                if r.author:
                    caption_parts.append(f"by {r.author}")
                if r.duration:
                    mins = r.duration // 60
                    secs = r.duration % 60
                    caption_parts.append(f"⏱️ {mins}:{secs:02d}")
                
                st.caption(" • ".join(caption_parts))
                
                # Action buttons
                st.link_button("View", r.url, use_container_width=True)
                
                if st.button("Select", key=f"sel-{q}-{i}", use_container_width=True):
                    chosen[q] = {
                        # Store the selected item
                        "query": q,
                        "title": r.title,
                        "provider": r.provider,
                        "url": r.url,
                        "thumb": r.thumb,
                        "author": r.author,
                        "license": r.license,
                        "media_type": r.media_type,
                        "duration": r.duration,
                        "video_files": r.video_files if r.media_type == "video" else None,
                        "extra": r.extra
                    }
                    st.session_state["vmt_chosen"] = chosen
                    st.success(f"✅ Selected for '{q}'")
                    st.rerun()
        
        # Show currently selected item if any
        if q in chosen:
            st.success(f"✅ Currently selected: **{chosen[q]['title']}** from {chosen[q]['provider']}")
        
        st.write("")  # spacing

    st.markdown("---")
    st.subheader("Export")
    
    # Show summary of selections
    if chosen:
        st.info(f"📌 {len(chosen)} items selected out of {len(queries)} queries")
    
    colA, colB, colC, colD = st.columns(4)
    
    session = {
        "text": st.session_state.get("vmt_text", ""),
        "queries": queries,
        "selected": chosen,
        "media_type": media_type
    }
    
    sess_json = json.dumps(session, ensure_ascii=False, indent=2)
    
    colA.download_button(
        "⬇️ Save Session (.vmt.json)",
        data=sess_json,
        file_name=f"{export_base}.vmt.json",
        mime="application/json"
    )

    rows = [dict(query=q, **v) for q,v in chosen.items()]
    csv_data = ""
    if rows:
        import csv
        from io import StringIO
        output = StringIO()
        fields = sorted({k for r in rows for k in r.keys()})
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        csv_data = output.getvalue()
    
    colB.download_button(
        "⬇️ Cue Sheet CSV",
        data=csv_data,
        file_name=f"{export_base}.csv",
        mime="text/csv"
    )
    
    colC.download_button(
        "⬇️ Results JSON",
        data=json.dumps(rows, ensure_ascii=False, indent=2),
        file_name=f"{export_base}.json",
        mime="application/json"
    )
    
    colD.download_button(
        "⬇️ Shotlist CSV",
        data=csv_data,
        file_name=f"{export_base}.shotlist.csv",
        mime="text/csv"
    )
else:
    st.info("👈 Start by analyzing text in the tabs above to generate queries.")
