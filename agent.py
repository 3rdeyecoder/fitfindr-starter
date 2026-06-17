"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.
    """
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


def _parse_query(query: str) -> dict:
    """Extract description, size, and max_price from the user's text query."""
    normalized = query.strip()
    parsed = {"description": normalized, "size": None, "max_price": None}

    price_patterns = [
        r"\b(?:under|below|less than|max(?:imum)?|<=)\s*\$?(\d+(?:\.\d+)?)\b",
        r"\$?(\d+(?:\.\d+)?)\s*(?:or less|or under|and under|max(?:imum)?|<=?)\b",
    ]
    for pattern in price_patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            parsed["max_price"] = float(match.group(1))
            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
            break

    size_match = re.search(r"\bsize\s*[:=]?\s*([A-Za-z0-9/]+)\b", normalized, flags=re.IGNORECASE)
    if size_match:
        parsed["size"] = size_match.group(1).strip()
        normalized = re.sub(r"\bsize\s*[:=]?\s*[A-Za-z0-9/]+\b", "", normalized, flags=re.IGNORECASE)

    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"^(i['’]?m|i am|i'm|im|looking for|searching for|want|wanting|need|find|find me|looking to find)\s+", "", normalized, flags=re.IGNORECASE)
    if normalized:
        parsed["description"] = normalized
    else:
        parsed["description"] = query.strip()

    return parsed


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.
    """
    session = _new_session(query, wardrobe)
    session["parsed"] = _parse_query(query)

    description = session["parsed"]["description"]
    size = session["parsed"]["size"]
    max_price = session["parsed"]["max_price"]

    results = search_listings(description, size=size, max_price=max_price)
    session["search_results"] = results
    if not results:
        session["error"] = (
            "I couldn't find any thrift listings matching that search. "
            "Try broadening the description or relaxing the size or price filter."
        )
        return session

    session["selected_item"] = results[0]
    session["outfit_suggestion"] = suggest_outfit(results[0], wardrobe)
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], results[0])
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
