---
name: sommelier
description: Ingest, organize, and summarize household wine information from bottle-label photos, tasting notes, cellar inventory, or purchase logs. Use when Justin wants to log wines, identify bottles from one or more label images, group multiple photos into a single wine record, or turn a Slack batch of wine photos into structured wine entries.
---

# Sommelier

Use this skill to turn loose wine information into structured records.

## Workflow

1. Gather the candidate inputs: label photos, free-text notes, vintage if known, purchase context if known.
2. Group images by bottle before extracting data. Never assume one image equals one wine.
3. Build a structured ingest record first, even if some wine fields are still unknown.
4. Extract or infer wine details from the grouped images.
5. Return a clean per-bottle summary and flag anything uncertain.

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

Use `status: needs_review` when any core field is uncertain.

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
