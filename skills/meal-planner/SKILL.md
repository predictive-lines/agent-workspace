---
name: meal-planner
description: >
  Generate weekly household meal plans (3 dinners/week) with recipes, shopping lists, and nutritional info.
  Use when: (1) planning meals for the week, (2) generating a shopping list, (3) logging meal feedback,
  (4) updating family food preferences, (5) browsing or searching past meal plans.
  Triggers on phrases like "meal plan", "what should we eat", "dinner ideas", "shopping list",
  "grocery list", "meal feedback", "food preferences", "recipe".
---

# Meal Planner

Plan 3 dinners per week for a family of 4 with specific preferences and dietary restrictions.

## Planning Day

**Saturday** is meal planning day. Generate the plan for the upcoming Mon–Sun week. This gives time to load the Kroger cart Saturday, schedule delivery for Sunday/Monday, and have ingredients ready for the first meal.

## Family Preferences

Load `references/family-preferences.json` for current preferences. Key constraints:

- **Justin:** No onions of any kind (garlic OK)
- **Jaclyn:** No avocado; loves soups, salads, curries, sweet potatoes, fish
- **Cora (14):** Asian-inspired, bang bang shrimp/chicken, tacos, sausage, pot pie
- **Eve (12):** Pasta, smash burgers, steak, ham, fried foods, pot pie; generally won't eat fish

**Hard rule:** Each weekly meal should be something at least 3 of 4 core family members will enjoy. Across the 3 meals combined, every person must have at least 1 meal they're happy with.

**No-onion compliance:** Replace onions/shallots/scallions/leeks with: extra garlic, fennel bulb, celery, or omit. Never include onion powder or onion-containing premade sauces without flagging it.

## Meal Complexity

- Most meals: 30-45 min, executable by a 12-14 year old (clear instructions, no advanced knife skills, limited stovetop juggling)
- Occasional "Sunday cook": up to 90 min, can be more complex
- Tag each recipe: `difficulty: easy | medium | sunday-project`

## Portion Sizing

Size each entree for **4-6 servings** depending on who's home that week. Let the recipe dictate natural protein quantities — do NOT override with fixed minimums.

**Attendance scaling (check with Justin each week or use default):**

| Scenario | Who's Home | Servings | Salad | Sweet Potatoes | Sides |
|---|---|---|---|---|---|
| **Everyone home** (default) | Justin + Jaclyn + Cora + Eve | 6 | Big batch (Justin eats most) | Normal | Full |
| **Justin traveling** | Jaclyn + Cora + Eve | 4 | Skip entirely | Normal | Scaled down |
| **Jaclyn traveling** | Justin + Cora + Eve | 4 | Big batch (Justin still wants it) | Light or skip | Scaled down |

- **Sides:** Scale to last across both entree nights where practical.
- **When in doubt, target the midpoint** — enough for comfortable seconds but not a third night of the same dish.
- **Protein:** Follow the recipe's natural proportions for the target serving count. Don't artificially inflate.

## Workflow: Queue a Meal

Add a specific recipe to `references/meal-queue.json` for an upcoming week's plan. Queued meals are locked in — when generating that week's plan, queued meals are used first and the remaining slots are filled around them.

1. Read `references/meal-queue.json`
2. Add the meal with full recipe details (ingredients, method, nutrition, freshness notes)
3. Set `target_week` to the Monday of the intended week (or `"next"` if unspecified)
4. Write updated file back
5. When generating a plan, check the queue first — consume any meals targeted for that week, then fill remaining entree/side slots normally

## Workflow: Generate a Meal Plan

**Step 0 (MANDATORY): Ask who's home this week.** Do NOT generate the plan until attendance is confirmed. Use the attendance_scaling table in preferences to set serving count, salad, and side sizing. Default assumption is everyone home, but ALWAYS confirm first.

1. Read `references/family-preferences.json` for current preferences
2. Read `references/feedback-log.json` for recent feedback (avoid recently disliked meals, favor hits)
3. Read `references/favorites.json` for the favorites index — aim to include a favorite every 2-3 weeks to keep proven hits in rotation
4. Read `references/meal-queue.json` — any queued meals for this week are locked in; plan around them
5. Select 3 dinner entrees + 3-4 shared sides for the week, ensuring:
   - The overlap constraint is met (everyone has ≥1 appealing meal)
   - No hard restrictions are violated (onions, avocado)
   - Variety from recent weeks (check feedback log for last 4 weeks)
   - Mix of protein types across the 3 meals
   - Sides rules are met (see Sides Strategy below)
6. Assign the meals to the standard slots unless Justin says otherwise:
   - **Sunday:** the most difficult / longest recipe
   - **Tuesday:** something easy enough for the girls to make
   - **Thursday:** a one-pot pasta + meat style dish that Beth can make
7. For each meal, produce:
   - **Recipe** with a full measured ingredient list (specific amounts, units, and any scaling needed for the week)
   - **Step-by-step instructions** that are complete enough to cook from without guessing; do not use shorthand like "make the sauce" or "cook until done" when a more explicit instruction is possible
   - **Prep/cook time** and difficulty tag
   - **Nutritional info** per serving: serving size (grams), calories, protein (g), carbs (g), fat (g), fiber (g)
   - **Appeal tags** showing which family members this targets
   - **Notes / tips** for substitutions, onion-compliance, and any role-based context (for example: good Tuesday girls' meal vs Thursday Beth meal)
5. Produce a **combined shopping list** grouped by store section (produce, protein, dairy, pantry, frozen, etc.)
   - Mark pantry staples with `(pantry staple)` — include them but flag them so Justin can skip what he has
   - Quantities sized for 4 servings per meal (adjust if sides vary)
6. Write the plan to Notion (see Output section)

## Nutritional Estimates

Estimate nutrition using standard USDA values. Be honest about precision — label as "estimated" not "exact." Include per-serving:
- Serving size in grams
- Calories (kcal)
- Protein (g)
- Total carbs (g)
- Total fat (g)
- Fiber (g)

## Output: Notion

Create meal plan pages under the **Meal Planning** page in Notion (parent of `ai-space`).

Structure each weekly plan as a Notion page:
```
Meal Planning/
  └── Week of [Mon date] - [Sun date]/
        ├── Meal 1: [Name] — [appeal tags]
        │     Full measured recipe + step-by-step instructions + nutrition
        ├── Meal 2: [Name] — [appeal tags]
        │     Full measured recipe + step-by-step instructions + nutrition
        ├── Meal 3: [Name] — [appeal tags]
        │     Full measured recipe + step-by-step instructions + nutrition
        ├── Sides (3-4 for the week)
        │     Salad + 2-3 other sides with measured recipes/nutrition
        └── Shopping List
```

Use headings, toggle blocks for recipes, and a bulleted list for the shopping list. Include a callout block at the top summarizing: who each meal targets, total estimated grocery cost range, and any notes.

### Printable Views (required)

Every weekly plan must include two **child pages** (not inline sections) linked from the main meal plan page. Child pages print cleanly from Notion.

Add a "🖨️ Printable Pages" section at the bottom of the main page with links to both child pages.

**Child Page 1: 🖨️ Recipe Cards**
- Simplified, fridge-friendly cooking instructions for each meal and side
- Written for a 12-14 year old to follow independently
- Include: a measured ingredient list (plain language, no "(pantry staple)" tags), numbered steps in ALL CAPS action-verb format ("COOK THE MEAT", "SLICE THE STEAK")
- Measurements are required on the printable cards too. Do not compress ingredient lists into vague summaries like "veggies" or "seasonings" when the cook needs the exact amount.
- After the ingredient list, add a short `WHAT EACH INGREDIENT DOES` explanation whenever the role of ingredients is not obvious from the title alone (especially binders, finishing sauces, optional thickeners, or ingredients that are used in different stages)
- Every meaningful ingredient on the card must appear in either the numbered steps or the `WHAT EACH INGREDIENT DOES` note. Do not leave ingredients hanging with no procedural explanation
- Be explicit about stage separation when needed: e.g. tell Justin whether soy sauce goes in the meatball mix vs. whether teriyaki sauce is a post-bake glaze
- Include practical tips inline (e.g., "do NOT put it all in at once or it will steam instead of sear")
- Include reheat instructions for Night 2 of each meal

**Child Page 2: 🖨️ Meal Assembly Guide**
- How to assemble/plate each meal (the build, combine, and serve steps)
- Which side pairs with which meal
- Reheat instructions for Night 2 of each meal
- When a meal is build-your-own or has components added at different stages, explicitly say what goes on first, what stays on the side, and what gets added after reheating
- Do NOT include: dinner schedules (people decide what night), prep-ahead tips

### Notion Auth

```bash
NOTION_KEY=$(cat ~/.config/notion/api_key)
```

Use API version `2025-09-03`. The Meal Planning parent page must be created once (see Setup below), then weekly plans are child pages.

## Notion Page

The **Meal Planning** parent page lives under `ai-space`:
- **Page ID:** `3267e702-d98c-8165-a2bd-ea55507e46a7`
- **URL:** https://www.notion.so/Meal-Planning-3267e702d98c8165a2bdea55507e46a7

Use this ID as the parent when creating weekly meal plan pages.

## Workflow: Log Feedback

After meals are cooked, log feedback to `references/feedback-log.json`:

```json
{
  "meals": [
    {
      "date": "2026-03-17",
      "name": "Bang Bang Shrimp Tacos",
      "ratings": {
        "justin": {"score": 1, "notes": ""},
        "jaclyn": {"score": 1, "notes": "liked the slaw"},
        "cora": {"score": 1, "notes": "wants more sauce next time"},
        "eve": {"score": 0, "notes": "didn't like the shrimp"}
      },
      "would_make_again": true,
      "tags": ["tacos", "shrimp", "asian-inspired"]
    }
  ]
}
```

- `score`: 1 = liked, 0 = neutral, -1 = disliked
- Use feedback to weight future meal selection (favor scores ≥1, avoid -1)

### Auto-favorite detection

When logging feedback, if **all 4 members score ≥1** AND `would_make_again: true`, automatically add the meal to `references/favorites.json` (if not already there). Notify Justin when a meal gets auto-favorited.

## Workflow: Manage Favorites

The favorites index (`references/favorites.json`) tracks proven-hit recipes that should stay in rotation.

### Add a favorite

Triggered by: explicit request ("mark X as a favorite") or auto-detection from feedback (see above).

1. Read `references/favorites.json`
2. Add an entry:
   ```json
   {
     "name": "Bang Bang Shrimp Tacos",
     "added": "2026-03-19",
     "source": "feedback-auto | manual",
     "tags": ["tacos", "shrimp", "asian-inspired"],
     "appeal": ["justin", "jaclyn", "cora"],
     "recipe_summary": "Brief 1-2 sentence description of the dish",
     "last_planned": null,
     "times_planned": 0,
     "notes": ""
   }
   ```
3. Write updated file back

### Remove a favorite

Triggered by: explicit request ("remove X from favorites") or consistent negative feedback (any member scores -1 twice on the same recipe).

1. Read `references/favorites.json`
2. Remove the matching entry (or move to a `retired` array if you want history)
3. Write updated file back

### Browse favorites

When asked to show favorites, list them with name, tags, appeal, and how recently they were last planned.

### Using favorites in meal planning

- **Rotation target:** Include a favorite roughly every 2-3 weeks. Don't over-repeat — the point is rotation, not repetition.
- **Track usage:** When a favorite is included in a plan, update `last_planned` and increment `times_planned`.
- **Staleness check:** If a favorite hasn't been planned in 6+ weeks, prioritize it.
- **Still check feedback:** Even favorites can get stale. If recent feedback on a favorite drops (scores trending to 0), flag it for review rather than auto-scheduling.

## Workflow: Update Preferences

When family members report new likes/dislikes:

1. Read `references/family-preferences.json`
2. Update the relevant member's `likes`, `dislikes`, or `restrictions`
3. Add an entry to `references/feedback-log.json` → `preference_updates` array:
   ```json
   {"date": "2026-03-17", "member": "eve", "change": "added 'salmon' to likes", "reason": "tried it at restaurant"}
   ```
4. Write updated file back

## Grocery Ordering: Kroger API

Script: `scripts/kroger_api.py` — handles auth, product search, and cart operations.

### Setup
- Credentials: `~/.config/kroger/credentials.json`
- User tokens: `~/.config/kroger/tokens.json` (after OAuth flow)
- Brighton store ID: `01800638`

### Product Search
```python
from scripts.kroger_api import search_products
results = search_products("sweet potato", location_id="01800638")
# Returns: [{upc, description, items: [{price: {regular, promo}, size}]}]
```

### Add to Cart
```python
from scripts.kroger_api import add_to_cart
add_to_cart([
    {"upc": "0000000004816", "quantity": 4},  # 4 sweet potatoes
    {"upc": "0000000004688", "quantity": 2},  # 2 red bell peppers
])
# Requires user OAuth token — run `python3 scripts/kroger_api.py auth` first
```

### Shopping Split Strategy
- **Costco (Green Oak MI):** Bulk proteins, dairy, tortillas, rice, butter — anything freezable/long shelf life
- **Kroger (Brighton MI):** Fresh produce, herbs, spices, bread — perishables that can't be portioned/frozen
- **Cheese rule:** Always prefer block over pre-shredded. Better melting, no anti-caking agents. **Never use American cheese singles** — use sliced cheddar if a slice is needed (burgers, etc.), block cheddar otherwise.
- **No decorative garnishes:** Skip parsley sprigs, cilantro for garnish, etc. Only include an ingredient if it adds meaningful flavor to the dish.
- **Fresh over canned/jarred:** Always prefer whole fresh fruits and vegetables. When searching Kroger, actively filter out canned/jarred matches (e.g., canned sweet potatoes, jarred jalapeños). Exception: ingredients that are inherently canned (chipotle in adobo, coconut milk, etc.).

### Delivery Timing
Kroger delivery slots fill up fast. When generating a meal plan, load the Kroger cart **at least 1 day before the first meal is needed** — ideally when the plan is generated. Flag this to Justin when posting the plan.

### Kroger Login Credentials
Stored in `~/.config/kroger/credentials.json` under keys `username` and `password`. Use these for browser-based login when needed.

### Checkout Workflow (Browser Relay)
The Chrome extension relay is used for checkout — it runs inside Justin's real Chrome session with existing Kroger login cookies.

**Requirements:** A Kroger tab must be open in Chrome with the OpenClaw Browser Relay extension attached (badge shows ON). Justin attaches it manually; the agent can then navigate freely.

**Full flow:**
1. Generate meal plan → load Kroger cart via API (`add_to_cart()`)
2. Notify Justin: "Cart is loaded — please attach the Kroger tab in Chrome so I can schedule delivery"
3. Once Justin confirms relay is connected:
   - Navigate to `https://www.kroger.com/checkout` via browser tool (`profile="chrome-relay"`)
   - Select the earliest available delivery slot
   - Proceed through checkout (confirm items, address, payment already on file)
   - Extract the confirmed delivery window
4. Add delivery window to the Miller family calendar (`miller-family-calendar@oneoaks.net`)
5. Notify Justin with delivery time and Notion plan link

**Browser relay profile:** `chrome-relay`
**Fallback:** If relay not available, load cart via API and ask Justin to checkout manually, then paste the delivery window back.

### Workflow: Assemble Cart
1. Generate meal plan → shopping list
2. For Kroger items: search each ingredient via API, pick best match (prefer fresh/whole over pre-packaged)
3. **Present the proposed Kroger cart to Justin and wait for explicit approval before calling `add_to_cart()`**. The Kroger API is add-only (no delete/clear) and clearing the cart manually is tedious (one item at a time). Never load the cart without permission.
4. Once approved: Add all Kroger items to cart via `add_to_cart()`
5. Notify Justin: "Kroger cart is loaded — review and checkout at kroger.com"
6. For Costco: list items + aisle suggestions (no API available yet)

## Shopping List Format

Group by section, mark staples:

```
## Produce
- 2 lbs sweet potatoes
- 1 head garlic (pantry staple)
- 1 bunch cilantro
- 2 limes

## Protein
- 1.5 lbs shrimp (peeled, deveined)
- 1 lb Italian sausage

## Dairy
- 1 cup sour cream
- 2 cups shredded cheddar

## Pantry
- Soy sauce (pantry staple)
- Rice vinegar (pantry staple)
- Sriracha (pantry staple)
- 1 box penne pasta (pantry staple)

## Frozen
- (none this week)
```

## Overlap Strategy

Finding meals that work for everyone is the hard part. Use these proven overlap zones:

| Overlap Zone | Works For | Example Meals |
|---|---|---|
| Tacos/quesadillas | All 4 | Build-your-own taco bar, quesadilla night |
| Pasta dishes | Cora, Eve, Justin, Jaclyn (if not too heavy) | Baked ziti, pasta bake, sausage pasta |
| Pot pie | All 4 | Chicken pot pie, beef pot pie |
| Asian-inspired (no fish) | Cora + Justin + Jaclyn; Eve if fried | Fried rice, stir-fry with rice |
| Soup + sandwiches | Jaclyn + Eve; others if hearty | Loaded baked potato soup + grilled cheese |
| Smash burgers / sliders | Eve + Justin; others usually game | Smash burger night with sweet potato fries |
| Sausage-based | Cora + Justin + Jaclyn | Sausage sheet pan, sausage pasta |
| Curry (mild) | Jaclyn + Justin; kids if mild | Mild coconut curry with rice |

When stuck, default to "build your own" format (taco bar, burger bar, rice bowl bar) — lets each person customize.

## Weekly Sweet / Treat

Do **not** include a weekly sweet/treat in meal plans by default. The family tends to go off script for sweets, so omitting this saves planning time, Notion space, and shopping-list cleanup. Only add a sweet if Justin explicitly asks for one that week.

If a sweet is explicitly requested, keep it separate from the default dinner workflow and clearly group its ingredients so they can be included or skipped intentionally.

## Sides Strategy

Plan **3-4 sides per week** shared across both entrees (not per-meal). At least one side must be a salad.

### Salad Side (required weekly)

- **Always include one salad** as a weekly side.
- **Lettuce variety matters:** Rotate through romaine, mixed greens, arugula, butter lettuce, spinach, etc. Don't default to the same type every week.
- **Toppings/add-ins:** More variety is better — cherry tomatoes, cucumbers, shredded carrots, radishes, bell peppers, nuts/seeds, dried cranberries, feta, etc. Must be ingredients Kroger can deliver (keep it practical).
- **Size depends on who's eating it:**
  - If Justin is the primary salad eater → make a big batch salad that keeps for several days.
  - If it's mostly Jaclyn and the girls → small salad, sized to be finished within 2 days (freshness over volume).
  - Default assumption: Justin eats most of the salad → size up. Adjust if feedback indicates otherwise.
- **Dressing:** Include a simple homemade dressing or specify a quality store-bought option.

### Remaining Sides (2-3 more)

- **Prioritize healthy options:** High fiber, colorful vegetables, whole-food ingredients.
- **Minimize processed foods:** No frozen tater tots, boxed mac & cheese, etc. Keep it whole-food-forward.
- **Starch limit:** At most 1 starchy side per week (roasted potatoes, rice, bread, etc.), and even then keep the serving size modest. Sweet potatoes count as a starch but are preferred over white potatoes.
- **Color variety:** Aim for a range of vegetable colors across the 3-4 sides — greens, oranges, reds, purples. More color diversity = better nutrition and plate appeal.
- **Good side examples:** Roasted broccoli, sautéed green beans with garlic, roasted carrots, steamed edamame, roasted Brussels sprouts, sautéed zucchini, beet salad, roasted cauliflower, cucumber/tomato salad.
- **Each side should pair well with at least one of the 2 entrees**, but most sides should work with both.
