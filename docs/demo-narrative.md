# Glutenix Demo Narrative

This document is a practical positioning note for demos, README excerpts, portfolio descriptions, and short posts. It should stay concrete: Glutenix is a decision-support workflow for gluten-free formulation, not a finished food product and not a replacement for physical testing.

## One-Liner

Glutenix helps narrow gluten-free formulation experiments by ranking candidate blends, exposing evidence gaps, and turning selected candidates into lab-ready test packages.

## Short Pitch

Gluten-free product development is expensive because many variables interact at once: flour family, starch type, hydrocolloids, proteins, hydration, heat, fermentation, cooking process, and flavor. Glutenix does not try to remove experiments. It tries to make them more intentional.

The current workflow can generate formulation candidates for bread and fresh pasta, save simulation history, mark decisions, create dossiers and physical-test protocols, record measured results, and compare measurements against predictions. Every output keeps model limitations visible, especially when a candidate is outside structured literature coverage.

## What To Show In A Demo

Use a saved candidate if the local database is available. Current useful examples are candidate `#61` for Pane and candidate `#131` for Pasta fresca.

### 1. Rank Or Reuse Candidates

```bash
uv run glutenix rank-pane --preset bobs-inspired --blend-samples 300 --process-samples 40 --top 10 --seed 42 --save-run --notes "commercial-inspired bread baseline"
uv run glutenix rank-application --application "Pasta fresca" --preset pasta-rice-structure-v1 --blend-samples 120 --process-samples 20 --top 10 --seed 20260621 --save-run --notes "pasta v1 calcium-alginate baseline"
```

Demo point: the system produces ranked hypotheses, not final recipes.

### 2. Inspect Saved History

```bash
uv run glutenix runs list
uv run glutenix runs show 14
uv run glutenix candidates mark 131 --status promising --notes "best current pasta v1 candidate"
```

Demo point: formulation work becomes traceable. Good and bad candidates can be preserved instead of rediscovered.

### 3. Generate A Lab Package

```bash
uv run glutenix lab package \
  --candidate-id 61 \
  --candidate-id 131 \
  --output-dir tmp/lab-package \
  --batch-g 500
```

Demo point: the output is practical: dossier, scaled protocol, and ready-to-edit recording commands.

### 4. Show Evidence Limits

```bash
uv run glutenix coverage gaps --application Pane --candidate-id 61 --json tmp/candidate-61-coverage.json
uv run glutenix coverage gaps --application "Pasta fresca" --candidate-id 131 --json tmp/pasta-candidate-131-coverage.json
```

Demo point: the project is intentionally cautious. It reports coverage, calibration limits, missing ingredients, and extrapolation risks.

### 5. Record Real Results Later

```bash
uv run glutenix experiments record --candidate-id 61 \
  --metric specific_volume_cm3_g:VALUE \
  --metric crumb_hardness_n:VALUE \
  --condition dry_blend_g:500 \
  --condition water_added_g:VALUE \
  --notes "replace with physical test notes"

uv run glutenix candidates feedback 61
uv run glutenix feedback summary --application Pane
```

Demo point: physical testing closes the loop. Feedback is diagnostic and does not silently recalibrate the model.

## Current Concrete Examples

### Pane Candidate `#61`

Best current bread candidate from saved runs.

- Status: `test_next`
- Score: `0.7596`
- Formula direction: sorghum, tapioca, potato, corn, pea protein, guar, xanthan
- Strength: balanced protein, viscosity, predicted volume, and flavor score
- Caveat: still needs physical bake validation

### Pasta Candidate `#131`

Best current Pasta fresca V1 candidate.

- Status: `promising`
- Score: `0.7140`
- Formula direction: high-amylose rice, brown rice, sweet rice, soy protein isolate, sodium alginate, curdlan, konjac
- Process direction: calcium-alginate fresh pasta baseline
- Caveat: experimental workflow, needs cooking-loss and texture measurements

## What Glutenix Is Not

- Not a validated commercial recipe generator.
- Not a sensory-panel replacement.
- Not a claim that heuristic simulation is enough without physical tests.
- Not an automatic ML calibration system.
- Not a medical or nutritional recommendation tool.

## What Makes It Interesting

- It treats formulation as an evidence-aware workflow, not a one-shot recipe prompt.
- It keeps simulation history and candidate decisions in the database.
- It separates prediction, coverage, protocol generation, experiment recording, and feedback.
- It can support multiple applications while keeping their metrics separate.
- It is honest about uncertainty: confidence, coverage, risk flags, and OOD warnings are part of the output.

## Short LinkedIn-Style Draft

I have been building Glutenix, a small open-source system for gluten-free formulation experiments.

The goal is simple: reduce random trial-and-error before physical testing. Glutenix ranks candidate blends for applications like bread and fresh pasta, saves the simulation history, highlights literature coverage gaps, generates lab-ready protocols, and later compares real measurements against predictions.

It is not a recipe generator and it does not replace experiments. The useful part is the workflow: simulate, shortlist, document assumptions, test, and feed results back into a traceable system.

Current status: bread has a complete CLI-first pre-lab loop; fresh pasta has an experimental V1 workflow. Next work is improving literature coverage and validating candidates with physical tests.

## Portfolio Description

Glutenix is an evidence-aware formulation simulator for gluten-free products. It combines ingredient-property modeling, application-specific scoring, literature coverage diagnostics, candidate decision tracking, physical-test protocol generation, and measured-vs-predicted feedback. The project is intentionally CLI-first and transparent about model limits, making it a practical scientific notebook for formulation work rather than a black-box recipe generator.
