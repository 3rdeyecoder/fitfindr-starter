# FitFindr

FitFindr is an AI-powered thrift shopping assistant. You describe what you're looking for, and the agent searches a mock secondhand listings dataset, suggests an outfit using your existing wardrobe, and generates a shareable caption — all in one planning loop.

## What's Included

```
fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```
---

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root with your Groq API key (free at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

## Running the App

```bash
python app.py
```

Open the URL shown in the terminal (usually `http://localhost:7860`). Enter a query like `vintage graphic tee under $30, size M` and select a wardrobe option. All three output panels should populate on a successful search.

## Running Tests

```bash
python -m pytest tests/test_tools.py -q
```

---

## Tool Inventory

### `search_listings(description, size, max_price)`

**Purpose:** Searches the mock listings dataset for thrifted items that match the user's query. Filters by size and price ceiling if provided, then ranks remaining results by keyword relevance.

**Inputs:**
- `description` (str) — free-text keywords describing the item (e.g. `"vintage graphic tee"`)
- `size` (str | None) — optional size filter, case-insensitive (e.g. `"M"` matches `"S/M"`)
- `max_price` (float | None) — optional price ceiling; listings above this are excluded

**Output:** A list of matching listing dicts sorted best-match first, each containing `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. Returns an empty list if nothing matches — never raises an exception.

---

### `suggest_outfit(new_item, wardrobe)`

**Purpose:** Uses the LLM to generate 1–2 outfit ideas for the selected thrifted item. When the user has a wardrobe, it references specific pieces by name. When the wardrobe is empty, it returns general styling guidance instead of failing.

**Inputs:**
- `new_item` (dict) — the selected listing dict from `search_listings`
- `wardrobe` (dict) — a wardrobe dict with an `items` list; each item has `name`, `category`, `colors`, `style_tags`, and optional `notes`

**Output:** A non-empty string with outfit ideas. Always returns something — either LLM-generated styling or a hardcoded fallback if the LLM call fails.

---

### `create_fit_card(outfit, new_item)`

**Purpose:** Turns the outfit suggestion into a 2–4 sentence caption in a casual social media voice, mentioning the item name, price, and platform naturally.

**Inputs:**
- `outfit` (str) — the outfit description produced by `suggest_outfit`
- `new_item` (dict) — the selected listing dict, used to pull item name, price, and platform

**Output:** A caption string suitable for sharing. Returns a descriptive error string (not an exception) if `outfit` is empty or missing.

---

## How the Planning Loop Works

The agent doesn't just call tools in sequence — it makes a conditional decision after the first tool that determines whether the interaction continues.

**Step 1 — Parse the query.** The agent extracts three structured values from the user's natural language input: a `description` string, an optional `size`, and an optional `max_price`. For example, `"vintage graphic tee under $30, size M"` becomes `description="vintage graphic tee"`, `size="M"`, `max_price=30.0`.

**Step 2 — Search listings (decision point).** The agent calls `search_listings` with the parsed values. If the result is an empty list, the agent sets an error message and returns immediately — it does not call `suggest_outfit` or `create_fit_card`. This is the only branch in the loop, and it's intentional: there's no point generating outfit advice for an item that doesn't exist.

**Step 3 — Select the top result.** If results were found, the agent picks `results[0]` (highest relevance score) as `selected_item` and stores it in the session.

**Step 4 — Suggest an outfit.** The agent calls `suggest_outfit(selected_item, wardrobe)` and stores the returned string as `outfit_suggestion`.

**Step 5 — Generate the fit card.** The agent calls `create_fit_card(outfit_suggestion, selected_item)` and stores the result as `fit_card`.

**Step 6 — Return the session.** The full session dict is returned to the Gradio interface, which maps each field to its output panel.

---

## State Management

The agent uses a single session dictionary to pass data between tools. It is initialized at the start of each interaction and written to at each step:

| Key | Set by | Used by |
|-----|--------|---------|
| `query` | agent init | — |
| `parsed` | `_parse_query()` | `search_listings` call |
| `search_results` | `search_listings` | agent (checks for empty list) |
| `selected_item` | agent (picks `results[0]`) | `suggest_outfit`, `create_fit_card`, UI |
| `wardrobe` | agent init (from UI) | `suggest_outfit` |
| `outfit_suggestion` | `suggest_outfit` | `create_fit_card`, UI |
| `fit_card` | `create_fit_card` | UI |
| `error` | agent (on empty results) | UI (shown instead of panels) |

No tool reads from the session directly — the agent extracts the right values and passes them as arguments. This keeps the tools independently testable.

---

## Error Handling

| Tool | Failure mode | What the agent does |
|------|-------------|---------------------|
| `search_listings` | No listings match the query | Sets `session["error"]` to a user-friendly message and returns early. `suggest_outfit` and `create_fit_card` are never called. |
| `suggest_outfit` | Wardrobe is empty | Returns general styling guidance (e.g. "pair with high-waisted bottoms and chunky boots") instead of failing. The agent still proceeds to `create_fit_card`. |
| `suggest_outfit` | LLM call raises an exception | Catches the exception and returns a hardcoded fallback string so the loop can continue. |
| `create_fit_card` | `outfit` string is empty | Returns a descriptive error string rather than raising an exception. The session still completes with a visible message in the fit card panel. |

**Concrete example from testing:** Querying `"designer ballgown size XXS under $5"` returns zero results from `search_listings`. The agent immediately sets `session["error"]` to `"I couldn't find any thrift listings matching that search. Try broadening the description or relaxing the size or price filter."` and returns. The `outfit_suggestion` and `fit_card` fields remain `None`. The Gradio UI displays the error message in the first panel and leaves the other two blank.

---

## Spec Reflection

The implementation stayed close to the plan in `planning.md`. A few things worth noting:

- **Query parsing added:** The plan described passing description, size, and max_price to the agent but didn't specify how those would be extracted from a natural language query. A `_parse_query()` function using regex patterns was added to handle phrases like `"under $30"` and `"size M"` without requiring the user to fill out a form.
- **Size matching generalized:** The spec said size filtering should be case-insensitive. The implementation goes further — `_tokenize_size()` splits combined sizes like `"S/M"` into individual tokens so a query for `"M"` still matches listings labeled `"S/M"`.
- **Fallback strings in LLM tools:** The spec said both `suggest_outfit` and `create_fit_card` should return a fallback instead of crashing. The implementation adds a `try/except` around the LLM call and returns a hardcoded string if the API fails, which wasn't explicitly specified but made the agent more robust during testing.

---

## AI Usage

### Instance 1 — Generating `search_listings`

**What I gave the AI:** The Tool 1 section from `planning.md`, including the input parameter names and types, the expected return format, and the failure behavior (return empty list, never raise).

**What it produced:** A working implementation that loaded listings with `load_listings()`, filtered by price and size, scored results by keyword overlap, and returned a sorted list.

**What I changed:** The initial size filtering used a plain string comparison, which meant a query for `"M"` would not match a listing labeled `"S/M"`. I replaced it with a `_tokenize_size()` function that splits combined sizes on `/` so `"S/M"` becomes `{"s", "m", "s/m"}` and the match works correctly. I also extended the relevance scoring beyond just the title field — the original only checked `title`, so I added `description`, `category`, `style_tags`, `colors`, and `brand` to `_flatten_listing_text()` so results rank more accurately.

---

### Instance 2 — Generating `suggest_outfit` and `create_fit_card`

**What I gave the AI:** The Tool 2 and Tool 3 sections from `planning.md`, including the wardrobe-aware prompt requirement and the instruction that empty wardrobes should get general styling advice rather than an error.

**What it produced:** Prompt-building functions that formatted the wardrobe items into a bulleted list and passed them to the LLM, with try/except fallback handling.

**What I changed:** The prompt for `create_fit_card` initially didn't include the item price or platform, so the caption output didn't mention where to buy it or how much it cost. I added those fields explicitly to the prompt so the generated caption feels like a real thrift find post. I also rewrote the fallback strings for both tools — the originals were generic ("something went wrong") and I replaced them with specific, on-brand alternatives that still give the user useful information even when the LLM call fails.

---

### Instance 3 — Planning loop and state management

**What I gave the AI:** The Planning Loop and State Management sections from `planning.md`, plus the architecture diagram.

**What it produced:** A `run_agent()` function that called all three tools in sequence and stored results in the session dict.

**What I changed:** The initial version called `suggest_outfit` and `create_fit_card` even when `search_listings` returned an empty list, which would crash downstream. I added the early return check so the agent stops immediately and sets `session["error"]` when no results are found. I also pulled query parsing into its own `_parse_query()` function with regex patterns for price (`"under $30"`) and size (`"size M"`) so the agent could handle natural language input instead of requiring structured fields.
