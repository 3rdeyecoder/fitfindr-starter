import os

import pytest

from agent import run_agent
from tools import search_listings
from utils.data_loader import get_example_wardrobe


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(item, dict) for item in results)


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=30)
    assert all(item["price"] <= 30 for item in results)


def test_agent_returns_error_for_no_results():
    session = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    assert session["error"] is not None
    assert session["fit_card"] is None
    assert session["outfit_suggestion"] is None


@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set",
)
def test_search_listings_can_parse_price():
    results = search_listings("vintage graphic tee under $30", size=None, max_price=30)
    assert len(results) > 0
