"""
Google Gemini AI Analyzer for Visual Media Tool

This module uses Google's Gemini API (free tier) to analyze scripts
and extract visual keywords for finding stock footage.

Free tier limits:
- 15 requests per minute
- 1,500 requests per day
- 1 million tokens per day
"""

import os
import json
import google.generativeai as genai
from typing import List, Tuple
from .analyzer import Analysis

def analyze_text_with_gemini(text: str) -> Analysis:
    """
    Use Google Gemini to analyze script text and extract visual search terms.
    
    Args:
        text: Script or transcript text to analyze
        
    Returns:
        Analysis object with keywords, entities, actions, and emotions
        
    Raises:
        ValueError: If GOOGLE_API_KEY is not set
        Exception: If API call fails
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found in environment. "
            "Get a free API key at https://makersuite.google.com/app/apikey"
        )
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # Use Gemini 1.5 Flash (fastest, free tier)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Craft the prompt with clear examples
    prompt = f"""You are a stock footage search expert. Extract SHORT search terms.

INPUT SCRIPT:
{text}

TASK: Generate search keywords for stock footage websites.

RULES (CRITICAL):
1. Each keyword = 1 to 3 words ONLY
2. Think: "What would I type into Pexels/Shutterstock search?"
3. NO long phrases
4. Simple, descriptive terms

EXAMPLE INPUT:
"A doctor examines a patient in a bright hospital room."

EXAMPLE OUTPUT:
{{
  "keywords": ["doctor examining", "hospital room", "medical checkup", "bright hospital", "patient care", "healthcare worker", "clinical examination", "medical professional", "hospital interior", "doctor patient"],
  "entities": ["hospital"],
  "actions": ["examining", "checking"],
  "emotions": ["professional", "caring"]
}}

NOW YOUR TURN - Extract keywords from the script above.
Output ONLY valid JSON (no extra text):
{{
  "keywords": [...],
  "entities": [...],
  "actions": [...],
  "emotions": [...]
}}"""

    try:
        # Generate response
        response = model.generate_content(prompt)
        
        # Extract text from response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first and last lines (``` markers)
            response_text = "\n".join(lines[1:-1])
            # Remove json language identifier if present
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()
        
        # Parse JSON
        data = json.loads(response_text)
        
        # Post-process keywords to enforce quality standards
        def clean_keywords(raw_keywords: List[str]) -> List[Tuple[str, float]]:
            """Clean up AI-generated keywords to be short and searchable"""
            cleaned = []
            seen = set()
            
            for keyword in raw_keywords:
                # Remove quotes and extra whitespace
                keyword = keyword.strip().strip('"').strip("'")
                
                # Skip if empty
                if not keyword:
                    continue
                
                # Count words
                words = keyword.split()
                word_count = len(words)
                
                # If too long (>4 words), try to extract useful phrases
                if word_count > 4:
                    # Try to find noun phrases at the end (more likely to be useful)
                    # Take last 2-3 words if they seem like a good phrase
                    if word_count >= 3:
                        # Try last 3 words
                        short_phrase = " ".join(words[-3:])
                        if short_phrase.lower() not in seen:
                            cleaned.append((short_phrase, 1.0))
                            seen.add(short_phrase.lower())
                        # Try last 2 words
                        short_phrase = " ".join(words[-2:])
                        if short_phrase.lower() not in seen:
                            cleaned.append((short_phrase, 1.0))
                            seen.add(short_phrase.lower())
                    # Skip this long keyword otherwise
                    continue
                
                # Good length (1-4 words), add it
                if keyword.lower() not in seen:
                    cleaned.append((keyword, 1.0))
                    seen.add(keyword.lower())
            
            return cleaned
        
        # Clean the keywords
        keywords = clean_keywords(data.get("keywords", []))
        
        # Quality check: if we got mostly garbage (long keywords), fall back to RAKE
        if len(keywords) < 5:
            print("Warning: Gemini returned poor quality keywords, falling back to RAKE analyzer")
            from .analyzer import analyze_text
            return analyze_text(text)
        
        # Clean entities, actions, emotions too (remove long ones)
        entities: List[str] = [
            e.strip() for e in data.get("entities", [])
            if len(e.split()) <= 4
        ]
        actions: List[str] = [
            a.strip() for a in data.get("actions", [])
            if len(a.split()) <= 3
        ]
        emotions: List[str] = [
            e.strip() for e in data.get("emotions", [])
            if len(e.split()) <= 2
        ]
        
        return Analysis(
            keywords=keywords,
            entities=entities,
            actions=actions,
            emotions=emotions
        )
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse Gemini response as JSON: {e}")
        print(f"Response was: {response_text[:200]}")
        # Fall back to basic analyzer
        from .analyzer import analyze_text
        return analyze_text(text)
        
    except Exception as e:
        print(f"Gemini API error: {e}")
        # Fall back to basic analyzer
        from .analyzer import analyze_text
        return analyze_text(text)


def test_gemini_connection() -> bool:
    """
    Test if Gemini API is configured and working.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Simple test
        response = model.generate_content("Say 'OK' if you can read this.")
        return "ok" in response.text.lower()
        
    except Exception as e:
        print(f"Gemini connection test failed: {e}")
        return False


# Convenience function that auto-falls back to basic analyzer
def analyze_text_smart(text: str, use_ai: bool = True) -> Analysis:
    """
    Smart analyzer that uses Gemini if available, otherwise falls back to basic.
    
    Args:
        text: Script text to analyze
        use_ai: Whether to try AI first (default True)
        
    Returns:
        Analysis object
    """
    if use_ai and os.getenv("GOOGLE_API_KEY"):
        try:
            return analyze_text_with_gemini(text)
        except Exception:
            pass
    
    # Fall back to basic analyzer
    from .analyzer import analyze_text
    return analyze_text(text)
