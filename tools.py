"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv(Path(__file__).parent / ".env")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_search_text(text: str) -> str:
    return (text or "").strip().lower()


def _tokenize_size(size: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9/]+", " ", (size or "").lower())
    tokens = set(token for token in normalized.split() if token)
    extra = set()
    for token in tokens:
        if "/" in token:
            extra.update(token.split("/"))
    return tokens | extra


def _matches_size(listing_size: str | None, requested_size: str | None) -> bool:
    if not requested_size:
        return True
    if not listing_size:
        return False
    requested = requested_size.strip().lower()
    return requested in _tokenize_size(listing_size)


def _flatten_listing_text(listing: dict) -> str:
    parts = [
        listing.get("title", ""),
        listing.get("description", ""),
        listing.get("category", ""),
        " ".join(listing.get("style_tags", [])),
        listing.get("brand") or "",
        " ".join(listing.get("colors", [])),
        listing.get("platform", ""),
    ]
    return " ".join(part for part in parts if part).lower()


def _score_listing(listing: dict, description: str) -> int:
    normalized_query = _normalize_search_text(description)
    if not normalized_query:
        return 1

    tokens = [token for token in re.split(r"[^a-z0-9]+", normalized_query) if token]
    if not tokens:
        return 1

    haystack = _flatten_listing_text(listing)
    score = 0
    for token in set(tokens):
        if token in haystack:
            score += 1
    if listing.get("category") and listing["category"].lower() in normalized_query:
        score += 1
    for tag in listing.get("style_tags", []):
        if tag.lower() in normalized_query:
            score += 1
    return score


def _extract_chat_response(response) -> str:
    if response is None:
        return ""
    choices = getattr(response, "choices", None)
    if choices is None and isinstance(response, dict):
        choices = response.get("choices")
    if not choices:
        return ""
    choice = choices[0]
    message = getattr(choice, "message", None)
    if message is None and isinstance(choice, dict):
        message = choice.get("message")
    if not message:
        return ""
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    return (content or "").strip()


def _call_llm(prompt: str, temperature: float = 0.8, max_tokens: int = 240) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a friendly fashion stylist who turns thrift finds into wearable outfit ideas and shareable captions.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_completion_tokens=max_tokens,
    )
    return _extract_chat_response(response)


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.
    """
    normalized_description = _normalize_search_text(description)
    listings = load_listings()
    candidates = []

    for listing in listings:
        if max_price is not None and listing.get("price") is not None:
            if listing["price"] > max_price:
                continue
        if not _matches_size(listing.get("size"), size):
            continue

        score = _score_listing(listing, normalized_description)
        if score <= 0 and normalized_description:
            continue

        candidates.append((score, listing))

    if not candidates:
        return []

    candidates.sort(key=lambda pair: (-pair[0], pair[1].get("price", float("inf"))))
    return [listing for _, listing in candidates]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.
    """
    wardrobe_items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []
    item_summary = (
        f"{new_item.get('title', 'Unknown item')} ({new_item.get('category', '')}),"
        f" colors: {', '.join(new_item.get('colors', []))},"
        f" style: {', '.join(new_item.get('style_tags', []))},"
        f" price: ${new_item.get('price', 'unknown')}, platform: {new_item.get('platform', 'unknown')}"
    )

    if not wardrobe_items:
        prompt = (
            "I have a thrifted item and no existing wardrobe items to pair it with. "
            "Here are the item details:\n"
            f"{item_summary}\n\n"
            "Give 1-2 friendly styling suggestions for this item. Explain what kinds of bottoms, shoes, outerwear, or accessories would work, and describe the vibe in plain language."
        )
    else:
        formatted_wardrobe = []
        for item in wardrobe_items:
            formatted_wardrobe.append(
                f"- {item.get('name')} ({item.get('category')}) | colors: {', '.join(item.get('colors', []))} | styles: {', '.join(item.get('style_tags', []))}"
                + (f" | notes: {item.get('notes')}" if item.get('notes') else "")
            )
        prompt = (
            "I have a thrifted item and an existing wardrobe. Suggest 1-2 outfit combinations that use this new item with pieces from the wardrobe. "
            "Reference wardrobe piece names when possible and keep the advice casual and visual. "
            "Finish with a short styling tip.\n\n"
            f"Item details: {item_summary}\n\n"
            "Wardrobe items:\n"
            + "\n".join(formatted_wardrobe)
        )

    try:
        suggestion = _call_llm(prompt, temperature=0.8, max_tokens=260).strip()
        if suggestion:
            return suggestion
    except Exception as e:
        print(f"[suggest_outfit] LLM call failed: {e}")

    if wardrobe_items:
        return (
            "I couldn't generate a full styling prompt right now, but this item would pair nicely with your existing pieces: try layering it with a neutral top, chunky shoes, and a classic black accessory for a balanced thrifted look."
        )

    return (
        "This piece has a clear vibe on its own: pair it with high-waisted bottoms, contrast it with a chunky shoe or boots, and keep accessories simple to let the thrifted find stand out."
    )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.
    """
    if not outfit or not outfit.strip():
        return (
            "I couldn't create a fit card because the outfit suggestion is missing. "
            "Try the search again or provide more details so I can generate a caption."
        )

    title = new_item.get("title", "this piece")
    platform = new_item.get("platform", "the listing")
    price = new_item.get("price")
    price_text = f"${price:.0f}" if isinstance(price, (int, float)) else str(price)

    prompt = (
        "Write a short, shareable outfit caption in a casual social media voice. "
        "Mention the thrifted item name, the price, and the platform naturally. "
        "Capture the vibe from the outfit description and keep it authentic, not like a product listing. "
        "Use 2-4 sentences.\n\n"
        f"Item: {title}\n"
        f"Price: {price_text}\n"
        f"Platform: {platform}\n"
        f"Outfit idea: {outfit}\n"
    )

    try:
        caption = _call_llm(prompt, temperature=0.9, max_tokens=200).strip()
        if caption:
            return caption
    except Exception:
        pass

    return (
        f"Thrifted {title} for {price_text} on {platform} and built it into a laid-back outfit that feels effortless and fresh. "
        f"Perfect for wearing with my favorite statement shoes and layered accessories."
    )
