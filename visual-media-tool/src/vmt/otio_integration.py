from __future__ import annotations
from typing import List
from dataclasses import dataclass

# This module is optional. We avoid importing opentimelineio unless the user installed it.

@dataclass
class OtioCue:
    label: str
    note: str | None = None

def extract_cues(otio_path: str) -> List[OtioCue]:
    try:
        import opentimelineio as otio  # type: ignore
    except Exception as e:
        raise RuntimeError("OpenTimelineIO is not installed. `pip install opentimelineio`. ") from e
    timeline = otio.adapters.read_from_file(otio_path)
    cues: List[OtioCue] = []
    for track in timeline.tracks:
        for clip in getattr(track, 'clips', []):
            md = getattr(clip, 'metadata', {}) or {}
            name = getattr(clip, 'name', None) or md.get('name') or 'Clip'
            note = md.get('note') or None
            cues.append(OtioCue(label=name, note=note))
    return cues
