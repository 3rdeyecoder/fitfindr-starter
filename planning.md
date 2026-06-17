# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset for thrifted items that match the user's description and optional filters. It returns relevant listings sorted by text-match relevance, with a price and size filter applied if provided.

**Input parameters:**
- `description` (str): User search terms for the desired item, such as "vintage graphic tee".
- `size` (str | None): Optional size filter, e.g. "M" or "8". If provided, only listings with a compatible size should be kept.
- `max_price` (float | None): Optional upper limit on price; if provided, only listings with `price <= max_price` are returned.

**What it returns:**
A list of listing dictionaries. Each dictionary contains `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. Results are sorted by relevance score (best match first).

**What happens if it fails or returns nothing:**
The tool returns an empty list. The agent should detect this and stop the interaction early, returning a helpful message that suggests broadening the search or relaxing size/price constraints.

---

### Tool 2: suggest_outfit

**What it does:**
Generates outfit recommendations for the selected thrifted item using the user's existing wardrobe. It either suggests specific combinations using named wardrobe pieces or gives general styling advice when the wardrobe is empty.

**Input parameters:**
- `new_item` (dict): The selected listing dict from `search_listings`, including title, description, category, style_tags, colors, price, and platform.
- `wardrobe` (dict): A wardrobe dict with an `items` list. Each item has `name`, `category`, `colors`, `style_tags`, and optional `notes`.

**What it returns:**
A non-empty string describing 1–2 outfit ideas. If the wardrobe contains items, the response should mention at least one specific wardrobe piece by name. If the wardrobe is empty, it should still return actionable styling guidance for the new item.

**What happens if it fails or returns nothing:**
If the wardrobe is empty, the tool returns a general styling advice string instead of crashing. If the LLM fails, the tool returns a fallback description like "I couldn't generate a polished outfit suggestion, but this item would pair well with..." so the agent can continue.

---

### Tool 3: create_fit_card

**What it does:**
Turns the outfit suggestion and thrift listing into a short, shareable caption that feels like a real outfit post.

**Input parameters:**
- `outfit` (str): The outfit description produced by `suggest_outfit`.
- `new_item` (dict): The selected listing dict, used to mention the item name, price, and platform.

**What it returns:**
A 2–4 sentence caption string suitable for social sharing. The caption should feel authentic, mention the item name, price, platform, and outfit vibe, and vary for different inputs.

**What happens if it fails or returns nothing:**
If `outfit` is empty or invalid, the tool returns a descriptive error string that explains the fit card could not be generated rather than raising an exception.

---

## Planning Loop

**How does your agent decide which tool to call next?**
1. Parse the user query into structured search parameters: `description`, `size`, and `max_price`.
2. Call `search_listings(description, size, max_price)`.
3. If `search_listings` returns an empty list, end the session early with an error message and do not call the later tools.
4. Otherwise, select the top listing from the search results and store it as `selected_item`.
5. Call `suggest_outfit(selected_item, wardrobe)`.
6. Call `create_fit_card(outfit_suggestion, selected_item)`.
7. Return the final session state.

This loop is conditional because the second and third tools only run when `search_listings` returns a non-empty result set.

---

## State Management

**How does information from one tool get passed to the next?**
The agent stores a session dict for each interaction. Session fields include:
- `query`: original user input
- `parsed`: extracted search description, size, and max_price
- `search_results`: results from `search_listings`
- `selected_item`: top listing chosen for styling
- `wardrobe`: the user's selected wardrobe
- `outfit_suggestion`: output from `suggest_outfit`
- `fit_card`: output from `create_fit_card`
- `error`: any early termination reason

The planning loop writes each tool result to the session. `suggest_outfit` receives `selected_item` and `wardrobe` from the session, and `create_fit_card` receives `outfit_suggestion` and `selected_item`.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | The agent sets `session["error"]` to a user-friendly message, returns early, and does not call `suggest_outfit` or `create_fit_card`. |
| suggest_outfit | Wardrobe is empty | The tool returns general styling advice for the item rather than failing; the agent still proceeds to `create_fit_card`. |
| create_fit_card | Outfit input is missing or incomplete | The tool returns a descriptive error string instead of throwing an exception, so the session still completes with a visible message. |

---

## Architecture

```mermaid
flowchart TD
    U[User query] --> P[Planning loop]
    P --> S1[search_listings(description, size, max_price)]
    S1 -->|results=[]| E[Error response]
    S1 -->|results[0]| SI[selected_item]
    SI --> S2[suggest_outfit(selected_item, wardrobe)]
    S2 --> OS[outfit_suggestion]
    OS --> S3[create_fit_card(outfit_suggestion, selected_item)]
    S3 --> FC[fit_card]
    P -->|stores| STATE[Session state]
    STATE -->|contains selected_item/outfit/fit_card| S2
    STATE -->|contains parsed query| S1
    E --> P
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**
- I will use the `Tool 1`, `Tool 2`, and `Tool 3` sections above as the prompt input.
- For `search_listings`, I expect the AI to generate a function that loads listings with `load_listings()`, filters by `size` and `max_price`, scores with keyword overlap, and returns sorted matches or an empty list.
- For `suggest_outfit`, I expect the AI to generate a prompt builder that creates a wardrobe-aware LLM request and handles empty wardrobes and API failures gracefully.
- For `create_fit_card`, I expect the AI to generate a caption prompt that mentions the item name, price, platform, and outfit vibe, and returns a fallback string when input is missing.
- I will verify each output by checking the function signature, failure handling, and by running isolated tests for `search_listings` plus sanity checks for prompt generation code.

**Milestone 4 — Planning loop and state management:**
- I will use the `Planning Loop` and `State Management` sections along with the architecture diagram as input.
- I expect the AI to generate a `run_agent()` implementation that parses the query, stores parsed parameters in `session["parsed"]`, conditionally stops when search results are empty, and wires `selected_item`, `outfit_suggestion`, and `fit_card` through the session.
- I will verify the output by ensuring the agent does not call `suggest_outfit` when search results are empty, and by running a happy-path query to confirm state flows correctly.

---

## A Complete Interaction (Step by Step)

FitFindr takes a natural language query, pulls a matching thrifted item from the listings dataset, and uses the user's wardrobe to build a styled outfit around it. `search_listings` triggers first and acts as a gatekeeper — if it finds nothing, the other two tools never run. When `suggest_outfit` or `create_fit_card` run into a problem, they return a fallback string instead of crashing so the user always gets a response.

**Example user query:** "I want a 90s windbreaker in size L, nothing over $45."

**Step 1:**
The agent parses the query into `description = "90s windbreaker"`, `size = "L"`, and `max_price = 45.0`. It calls `search_listings("90s windbreaker", size="L", max_price=45.0)`. The tool scores every listing against those keywords, drops anything above $45 or not in size L, and returns the ranked matches. The agent stores the full results list in `session["search_results"]` and checks whether it's empty. Since matches are found, it picks `results[0]` — say, a colorblock nylon track jacket for $38 on Depop — and saves it as `session["selected_item"]`.

**Step 2:**
The agent calls `suggest_outfit(selected_item, wardrobe)`. The tool sees the user has a wardrobe with items like white cargo pants and black high-tops, builds a prompt that names those pieces, and asks the LLM for 1–2 outfit combos. The LLM returns something like "Layer the track jacket over a fitted white tee, throw on your white cargo pants and black high-tops for a clean 90s athletic look." That string is saved as `session["outfit_suggestion"]`.

**Step 3:**
The agent calls `create_fit_card(outfit_suggestion, selected_item)`. The tool builds a prompt using the outfit description plus the item name, price, and platform, then asks the LLM to write a 2–4 sentence social caption. The result — something like "Grabbed this colorblock track jacket for $38 on Depop and it just works. Styled it with white cargos and my go-to high-tops for that effortless 90s athletic feel. Thrift first, always." — is saved as `session["fit_card"]`.

**Final output to user:**
The Gradio interface maps the three session fields to the three output panels:
- Top listing found: the colorblock track jacket details
- Outfit idea: the LLM-generated styling with wardrobe piece names
- Fit card: the shareable caption

**What happens if it fails:** If the query had been `"designer trench coat size XXS under $10"`, `search_listings` would return an empty list. The agent sets `session["error"]` to a message like "I couldn't find any thrift listings matching that search — try broadening the description or relaxing your filters" and returns immediately. `suggest_outfit` and `create_fit_card` are never called, and the error message appears in the first panel while the other two stay blank.
