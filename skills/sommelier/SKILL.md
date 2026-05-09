---
name: sommelier
description: Ingest, organize, and summarize household wine information from bottle-label photos, tasting notes, cellar inventory, purchase logs, or preference discussions. Use when Justin wants to log wines, identify bottles from one or more label images, group multiple photos into one wine record, track which wines Justin and Jaclyn liked or disliked, capture wineries/regions/grapes they gravitate toward, or suggest bottles they might like next.
---

# Sommelier

Use this skill to turn loose wine information into durable household wine records and preference signals.

## Workflow

1. Gather the candidate inputs: label photos, free-text notes, vintage if known, purchase context if known, and any reaction from Justin or Jaclyn.
2. Group images by bottle before extracting data. Never assume one image equals one wine.
3. Build a structured ingest record first, even if some wine fields are still unknown.
4. Extract or infer wine details from the grouped images.
5. Save the filled record under `data/sommelier/records/` and keep the raw batch manifest under `data/sommelier/batches/`.
6. If tasting feedback is present, update `data/sommelier/family-preferences.json` with per-person likes/dislikes plus household patterns.
7. Return a clean per-bottle summary, flag anything uncertain, and state the likely style signals worth reusing for future recommendations.

## Vision extraction

- Use the `image` tool for the actual label-reading step.
- Prefer `model: openai-codex/gpt-5.5` in this environment.
- Ask for strict structured extraction and explicitly allow `unknown` for illegible fields.
- If the host errors with `sharp` missing while processing Slack images, install it in the OpenClaw package dir with `npm install sharp` and retry.

## Bottle grouping rules

- Treat front/back/wraparound images as one bottle when the user says so or the images clearly belong together.
- Support multiple bottles in a single batch.
- Preserve the original image paths in the record for traceability.
- Prefer explicit user grouping over automatic guesses.

## Structured output shape

For each bottle, capture at least:

- `bottle_id`
- `image_paths`
- `producer`
- `wine_name`
- `vintage`
- `varietal`
- `region`
- `country`
- `confidence`
- `notes`
- `status`

Add these when available:

- `style`
- `subregion_notes`
- `price`
- `purchase_location`
- `tasted_on`
- `tasters`
- `ratings`
- `would_buy_again`
- `recommendation_signals`

Use `status: needs_review` when any core field is uncertain.

## Preference tracking

Treat household preference capture as first-class, not an afterthought.

- Keep separate taster profiles for Justin and Jaclyn when the input supports it.
- Distinguish bottle facts from taste judgments.
- Prefer concrete sensory or stylistic language over vague praise. Examples: `high acid`, `textural white`, `jammy Paso red`, `earthy Pinot`, `too oaky`.
- When only a general reaction is known, store it as a hypothesis rather than a conclusion.
- When suggesting future wines, ground the suggestion in patterns already seen in `family-preferences.json`.

## Script

Use `scripts/ingest_batch.py` to create a deterministic ingest manifest from a Slack or local image batch before doing higher-judgment extraction.

Example:

```bash
python3 skills/sommelier/scripts/ingest_batch.py \
  --source slack \
  --group-sizes 3,1,1 \
  --output /tmp/wine-batch.json \
  image1.jpg image2.jpg image3.jpg image4.jpg image5.jpg
```

The script does not perform OCR or vision extraction; it creates the batch record that later extraction steps should fill in.

After manifest creation, run vision extraction bottle-by-bottle or batch-wide and write the filled record to a durable JSON file under `data/sommelier/`.

## Current local storage

Use these files unless the user asks for a different backend:

- `data/sommelier/batches/*.json` — raw grouped photo manifests
- `data/sommelier/records/*.json` — extracted bottle records
- `data/sommelier/family-preferences.json` — per-person and household taste patterns

This local JSON store is the default v1. If the household later wants search, reports, or shared editing, add a synced backend after the capture workflow feels stable.
