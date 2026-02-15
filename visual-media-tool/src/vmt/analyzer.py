from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Dict, Iterable, Tuple
from collections import Counter, defaultdict

# ---- Simple RAKE-like keyword extraction ----
STOPWORDS = set("""a an and the of on in by to with from or for at as is are was were be been being it this that those these
you your yours we our ours they their theirs he she his her its i me my mine not no nor but if then than so such too very just
""".split())

PUNCT_SPLIT = re.compile(r"[\s,;:()\[\].!?\-\/]+")

@dataclass
class Analysis:
    keywords: List[Tuple[str, float]]
    entities: List[str]
    actions: List[str]
    emotions: List[str]

EMOTION_LEX = {
    "happy": ["joy", "happy", "cheer", "delight", "optimistic", "hopeful"],
    "sad": ["sad", "melancholy", "bittersweet", "lonely", "regret"],
    "angry": ["angry", "rage", "furious", "irritated", "frustrated"],
    "fear": ["fear", "anxious", "afraid", "tense", "worried"],
    "surprise": ["surprise", "shocked", "unexpected"],
    "calm": ["calm", "peaceful", "serene", "relaxed"],
    "romance": ["love", "romantic", "tender"],
    "hope": ["hope", "hopeful", "aspire"],
}

COMMON_VERBS = set("""cut run walk talk look see watch drive type scroll shoot cook eat drink dance sing cry laugh argue fight
open close enter exit hold push pull lift throw catch point think wait sit stand write wipe pour steam rise bloom glow drift click
""".split())

def _candidate_phrases(text: str) -> List[List[str]]:
    words = [w.lower() for w in PUNCT_SPLIT.split(text) if w]
    phrases = []
    phrase = []
    for w in words:
        if w in STOPWORDS:
            if phrase:
                phrases.append(phrase); phrase = []
        else:
            phrase.append(w)
    if phrase: phrases.append(phrase)
    return phrases

def _score_phrases(phrases: List[List[str]]) -> Dict[str, float]:
    freq = Counter()
    degree = Counter()
    for ph in phrases:
        unique = [w for w in ph if w]
        for w in unique:
            freq[w] += 1
            degree[w] += len(ph) - 1
    scores = {w: (degree[w] + freq[w]) / (freq[w] or 1) for w in freq}
    phrase_scores = {}
    for ph in phrases:
        s = sum(scores.get(w, 0) for w in ph)
        phrase_scores[" ".join(ph)] = s
    return phrase_scores

def extract_keywords(text: str, top_k: int = 25) -> List[Tuple[str, float]]:
    phrases = _candidate_phrases(text)
    scored = _score_phrases(phrases)
    return sorted(scored.items(), key=lambda x: x[1], reverse=True)[:top_k]

ENTITY_PATTERN = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b" )

def extract_entities(text: str, max_n: int = 20) -> List[str]:
    # Naive: proper-case sequences as 'entities'; filter common sentence starters
    raw = ENTITY_PATTERN.findall(text)
    ban = {"INT", "EXT", "DAY", "NIGHT"}
    out = []
    for e in raw:
        if e.upper() in ban: continue
        if len(e) < 3: continue
        out.append(e.strip())
    # dedupe preserving order
    seen = set(); ordered = []
    for e in out:
        if e not in seen:
            seen.add(e); ordered.append(e)
    return ordered[:max_n]

def extract_actions(text: str, max_n: int = 20) -> List[str]:
    words = [w.lower() for w in PUNCT_SPLIT.split(text) if w]
    counts = Counter(w for w in words if w in COMMON_VERBS or w.endswith("ing"))
    return [w for w,_ in counts.most_common(max_n)]

def extract_emotions(text: str) -> List[str]:
    t = text.lower()
    hits = []
    for label, kws in EMOTION_LEX.items():
        if any(k in t for k in kws):
            hits.append(label)
    # stable ordering
    order = ["happy","calm","hope","romance","surprise","fear","sad","angry"]
    return [e for e in order if e in hits]

def analyze_text(text: str) -> Analysis:
    kws = extract_keywords(text)
    ents = extract_entities(text)
    acts = extract_actions(text)
    emos = extract_emotions(text)
    return Analysis(keywords=kws, entities=ents, actions=acts, emotions=emos)

def build_queries(analysis: Analysis, limit: int = 12) -> List[str]:
    """
    Build search queries from analysis results.
    Smart enough to handle both basic RAKE output and AI-generated keywords.
    """
    top_terms = [k for k,_ in analysis.keywords[:15]]
    combos = []
    
    def add(q): 
        # Only add if it's a reasonable length (2-6 words) and not already added
        word_count = len(q.split())
        if q and q not in combos and 1 <= word_count <= 6:
            combos.append(q)
    
    # Add top keywords directly (AI often gives great 2-3 word phrases)
    for k in top_terms[:limit]:
        add(k)
            
    # Add entities as-is (usually good search terms)
    for e in analysis.entities[:4]:
        add(e)
    
    # Only combine if we don't have enough queries yet
    # This prevents over-combining when AI already gave good phrases
    if len(combos) < limit:
        # Combine actions with short keywords (1-2 words only)
        short_terms = [k for k in top_terms[:6] if len(k.split()) <= 2]
        for a in analysis.actions[:3]:
            for k in short_terms[:3]:
                if len(combos) >= limit:
                    break
                add(f"{a} {k}")
    
    return combos[:limit]
