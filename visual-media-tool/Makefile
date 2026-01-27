.PHONY: dev run test fmt

dev:
	python -m pip install -r requirements.txt

run:
	streamlit run app.py

test:
	python -m pytest -q

fmt:
	python - <<'PY'
import pathlib, sys
from pathlib import Path
for p in Path('src').rglob('*.py'):
    s=p.read_text(); p.write_text(s.rstrip()+"\n")
print("Trimmed trailing whitespace.")
PY
