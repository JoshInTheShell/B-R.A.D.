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
    
    # Craft the prompt
    prompt = f"""You are analyzing a script to find stock footage. Extract visual search terms.

Script:
{text}

Extract and provide:
1. **Visual Keywords**: 15 concrete, searchable terms (things that can be photographed/filmed)
   - Focus on: objects, locations, scenes, activities, visual elements
   - Avoid: abstract concepts, emotions without visual representation
   - Examples: "sunset", "city street", "coffee cup", "running person"

2. **Named Entities**: People names, place names, specific objects mentioned
   - Examples: "New York", "Golden Gate Bridge", "iPhone"

3. **Actions/Verbs**: Things happening that can be shown visually
   - Examples: "running", "typing", "cooking", "driving"

4. **Emotional Tones**: Mood keywords useful for stock footage search
   - Examples: "happy", "dramatic", "peaceful", "energetic"

Respond ONLY with valid JSON in this exact format (no markdown, no explanation):
{{
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "entities": ["Entity1", "Entity2"],
  "actions": ["action1", "action2"],
  "emotions": ["emotion1", "emotion2"]
}}

Be specific and visual. Each term should be something you could type into a stock footage search."""

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
        
        # Convert to Analysis format
        # Keywords need to be tuples of (keyword, score)
        keywords: List[Tuple[str, float]] = [
            (k, 1.0) for k in data.get("keywords", [])
        ]
        entities: List[str] = data.get("entities", [])
        actions: List[str] = data.get("actions", [])
        emotions: List[str] = data.get("emotions", [])
        
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
