from src.vmt.analyzer import analyze_text, build_queries

def test_basic_analysis():
    txt = "A barista wipes the counter. Steam rises. Hopeful mood."
    a = analyze_text(txt)
    assert a.keywords
    assert "wipes" in a.actions or any(k for k,_ in a.keywords)
    q = build_queries(a)
    assert isinstance(q, list) and len(q) > 0
