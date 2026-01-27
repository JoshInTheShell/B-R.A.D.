from __future__ import annotations
import csv, json
from typing import List, Dict, Any
from pathlib import Path

def export_csv(rows: List[Dict[str, Any]], path: str | Path) -> str:
    path = Path(path)
    if not rows:
        path.write_text("query,title,provider,url,thumb\n", encoding="utf-8")
        return str(path)
    fields = sorted({k for r in rows for k in r.keys()})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return str(path)

def export_json(rows: List[Dict[str, Any]], path: str | Path) -> str:
    path = Path(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return str(path)

def export_shotlist(mapping: Dict[str, Dict[str, Any]], path: str | Path) -> str:
    """mapping: query -> selected item dict"""
    path = Path(path)
    rows = [{"query": q, **item} for q, item in mapping.items()]
    return export_csv(rows, path)
