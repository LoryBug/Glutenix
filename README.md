# Glutenix

Glutenix is a simulation and optimization project for gluten-free flour blends.

The idea started from two places: the guided experimentation mindset behind Alchemix, and a practical personal need. As someone with celiac disease, I wanted a better way to reason about gluten-free foods before spending time, ingredients, and money on repeated trial-and-error batches.

Gluten-free formulation is difficult because small changes in flour, starch, hydrocolloid, hydration, heat, and process can completely change the result. Glutenix tries to make experimentation more intentional: simulate first, compare options, identify plausible candidates, and then test only the recipes that actually make sense.

The project is not a replacement for lab or kitchen testing. It is a decision-support tool for narrowing the search space.

## What It Does

Glutenix models gluten-free formulations from ingredients and process parameters, then scores or optimizes them for specific applications.

Current focus areas:

- Blend property calculation from ingredient composition.
- Fermentation and baking simulation for baked products.
- Pasta cooking simulation for gluten-free pasta systems.
- Process sweeps to compare many time/temperature/hydration settings.
- Application-specific target profiles for pizza, bread, sweet leavened doughs, pastry, and fresh pasta.
- Flavor heuristics to avoid technically good but unpleasant blends.
- Literature-backed calibration reports, especially for gluten-free pasta cooking loss.
- Bayesian optimization and Gaussian Process Regression for learning from experiments.

The intended workflow is:

1. Define candidate ingredients and bounds.
2. Simulate blend behavior and process conditions.
3. Rank candidates against the target application.
4. Run real tests only on the most promising formulations.
5. Feed experimental results back into the system over time.

## Why This Exists

Most gluten-free product development is noisy and expensive. Without gluten, structure has to come from starch gelatinization, proteins, fibers, hydrocolloids, emulsification, hydration management, and process control.

That usually means many failed attempts:

- Dough that does not hold gas.
- Bread that collapses or dries out.
- Pizza bases that are gummy or brittle.
- Pasta with high cooking loss or poor bite.
- Recipes that work once but fail when hydration or process changes.

Glutenix is built around a simple idea: experiments should still happen, but they should be informed experiments.

Instead of trying ten random recipes, the system should help answer questions like:

- Which blends are physically plausible for this application?
- Which ingredient ranges are likely to matter most?
- Which process parameters are worth testing?
- Is this prediction inside an area covered by literature, or is it extrapolation?
- What should I test next if I want to improve the model?

## Core Simulation Modules

### Blend Model

The blend calculator combines ingredient data into formulation-level properties:

- Protein, starch, fat, fiber, moisture, ash.
- Water absorption.
- Gelatinization temperature range.
- Amylose percentage.
- Hydrocolloid fraction.
- Approximate nutritional values.
- Viscosity index.

This is the base layer used by the simulation and optimization engines.

### Fermentation And Baking

For baked applications, Glutenix simulates fermentation and baking behavior from blend properties and process inputs.

The model estimates signals such as:

- Fermentation volume increase.
- Core temperature.
- Crust temperature.
- Gelatinization progress.
- Process quality against application targets.

This is useful for screening products such as pizza, bread, sweet leavened doughs, pastry, and biscuits.

### Pasta Cooking

The pasta simulator is currently the most literature-calibrated part of the project.

It estimates:

- Cooking loss.
- Water uptake.
- Swelling index.
- Firmness index.
- Stickiness index.
- Gelation index.
- Pregelatinization index.
- Syneresis index.
- Starch leaching index.
- Overall quality score.

It also returns calibration metadata:

- `process_family`
- `calibration_confidence`
- `calibration_score`
- `calibration_notes`

This is meant to make predictions more honest. A result inside a literature-covered region should not be treated the same as a pure extrapolation.

Current covered process families include:

- Fresh calcium-alginate pasta systems.
- Dried extruded rice pasta with KGM/curdlan or soy protein isolate.
- Generic fresh pasta as a lower-confidence heuristic mode.

## Optimization

Glutenix includes multiple optimization layers.

### Process Sweep

`POST /simulate/sweep` evaluates many process combinations for a fixed blend.

This is useful when the formulation is fixed but the process is not:

- Fermentation temperature.
- Fermentation duration.
- Baking/cooking temperature.
- Baking/cooking duration.

### Application Suggestion

`POST /optimize/application-suggest` searches blend proportions and process conditions for a target application.

It combines:

- Process score.
- Blend-property score.
- Flavor score.
- Pasta cooking metrics when the target is fresh pasta.
- Model confidence metadata that explains support level and risk flags.

The goal is not to output a magic recipe. The goal is to produce a ranked shortlist of candidates worth testing.

For quick bread experiments without starting the API, use the slim CLI:

```bash
uv run glutenix rank-pane --preset sorghum-baseline --blend-samples 100 --process-samples 20 --top 10 --seed 42
```

Available presets include `sorghum-baseline`, `bobs-inspired`, `schaer-inspired`, `freee-inspired`, and `quinoa-hpmc`. Add `--csv results.csv` or `--json results.json` for machine-readable output.

To preserve a scientific history of runs and candidate decisions in the database:

```bash
uv run glutenix rank-pane --preset bobs-inspired --blend-samples 300 --process-samples 40 --top 10 --seed 42 --save-run --notes "commercial-inspired baseline"
uv run glutenix runs list
uv run glutenix runs show 1
uv run glutenix candidates mark 1 --status test_next --notes "best protein/viscosity balance"
```

### Bayesian Optimization And GPR

The project includes Gaussian Process Regression and Bayesian Optimization components so that real experimental results can eventually guide future suggestions.

This is important because the current physics models are partly heuristic. The long-term direction is to combine:

- First-principles-inspired simulation.
- Literature calibration.
- User/lab experimental data.
- Model uncertainty.

## Literature Calibration

Glutenix stores structured literature records in `data/literature/` and compares simulator output against measured values.

Current pasta cooking calibration dataset:

- 40 records.
- 3 peer-reviewed sources.
- Main calibration metric: `cooking_loss_pct`.
- Auxiliary metrics: water absorption, swelling index, and water adsorption index where available.

Current sources include:

- Lux et al. 2023: calcium-alginate amaranth fresh pasta.
- Liu et al. 2026: extruded rice pasta with konjac glucomannan and curdlan.
- Detchewa et al. 2016: extruded rice spaghetti with soy protein isolate.

Current bread baking diagnostic dataset:

- 60 records.
- 9 peer-reviewed sources.
- Main metric: `specific_volume_cm3_g`.
- Auxiliary metrics include crumb hardness, porosity, moisture, water activity, and structure fields where available.

Current bread sources include:

- Singh and Adedeji 2026: proso millet cultivar gluten-free breads.
- Torres-Perez et al. 2026: additive-removal clean-label gluten-free bread.
- Loncaric et al. 2026: rice/whey and rice/chickpea gluten-free bread staling.
- Parsamajd et al. 2025: HPMC/xanthan/guar hydrocolloid-combination gluten-free breads.
- Belorio and Gomez 2020: hydration effects in rice/maize HPMC/psyllium/xanthan breads.
- Wojcik et al. 2021: pea-protein-enriched buckwheat/flaxseed gluten-free bread.
- Kahraman et al. 2022: raw/roasted/dehulled chickpea flour in rice-based gluten-free bread.
- Bianchi et al. 2026: tapioca starch/red lentil mixture-design gluten-free breads.
- Ghodosipoor et al. 2025: quinoa flour + HPMC + microbial transglutaminase CCD gluten-free bread optimization.

Important limitation: the linear correction in calibration reports is diagnostic only. It is not treated as production calibration.

Generated calibration-report sections can be refreshed with:

```bash
uv run python scripts/update_calibration_reports.py --write
```

Use `--check` in validation to fail when generated report tables are stale.

Useful files:

- `data/literature/pasta_cooking.jsonl`
- `docs/pasta-cooking-calibration-report.md`
- `docs/bread-baking-calibration-report.md`
- `docs/literature-extraction-template.md`
- `docs/application-targets-research.md`
- `docs/flavor-heuristic-model.md`

## API Overview

The backend is a FastAPI application.

Main endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Health check |
| `GET /ingredients` | List ingredient database |
| `POST /blends` | Create a blend from ingredient proportions |
| `POST /simulate` | Run fermentation and baking simulation |
| `POST /simulate/cooking` | Run gluten-free pasta cooking simulation |
| `POST /simulate/sweep` | Evaluate process parameter sweeps |
| `GET /simulate/target-profiles` | List application target profiles |
| `POST /optimize/suggest` | Generate generic optimized blend candidates |
| `POST /optimize/application-suggest` | Suggest blends/processes for a specific application |
| `GET /optimize/flavor-targets` | List flavor target profiles |
| `GET /calibration/pasta-cooking` | Compare pasta simulator against literature records |
| `GET /calibration/bread-baking` | Compare bread simulator against literature records |
| `GET /calibration/coverage` | Report literature-derived coverage ranges and OOD basis |
| `POST /experiments` | Store experimental observations |

Example pasta cooking request:

```bash
curl -X POST http://localhost:8000/simulate/cooking \
  -H "Content-Type: application/json" \
  -d '{
    "blend_id": 1,
    "water_temp_c": 98,
    "cooking_time_min": 6,
    "pasta_thickness_mm": 2,
    "water_to_flour_ratio": 6,
    "calcium_lactate_m": 0.1,
    "calcium_bath_time_min": 30,
    "dough_heat_temp_c": 80,
    "dough_heat_time_min": 60
  }'
```

The response includes physical metrics and calibration metadata, so the result can be interpreted as either literature-supported or more speculative.

## Frontend

There is a Vue 3 + Vite frontend for interacting with the API.

At this stage, the frontend is a useful interface, but the main value of the project is the simulation, optimization, calibration, and data model behind it.

Frontend stack:

- Vue 3.
- Vite.
- Axios.
- Chart.js.

## Running Locally

Requirements:

- Python 3.13+
- `uv`
- Node.js and npm for the optional frontend

Install Python dependencies:

```bash
uv sync
```

Create and seed the SQLite database:

```bash
uv run python -c "from glutenix.db.base import Base, engine; from glutenix.db.seed import seed_database; Base.metadata.create_all(engine); seed_database()"
```

Run the API:

```bash
uv run uvicorn glutenix.api.server:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

Interactive API docs:

```text
http://localhost:8000/docs
```

Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Run tests:

```bash
uv run pytest -q
```

Build the frontend:

```bash
cd frontend
npm run build
```

## Current Validation Status

The project currently has automated tests for:

- Ingredient and application API routes.
- Blend creation.
- Baking and fermentation simulation.
- Pasta cooking simulation.
- Process sweeps.
- Calibration loading and reporting.
- Flavor heuristic scoring.
- Bayesian optimization and GPR behavior.
- Application-level optimization.

Recent full validation should be checked with `uv run pytest -q`; avoid relying on stale hardcoded pass counts in docs.

## Development Workflow

Planning, issue templates, branch/PR conventions, review expectations, and ADR guidance are documented in `docs/development-workflow.md`.

## Project Philosophy

Glutenix is intentionally not presented as a fully calibrated food science platform yet.

The current models combine:

- Approximate ingredient data.
- Physics-inspired heuristics.
- Literature-derived calibration checks.
- Experimental-data infrastructure.
- ML/BO components for future learning.

That means predictions should be used to prioritize experiments, not to skip validation completely.

The practical goal is simple: help people working on gluten-free foods waste fewer attempts and make better decisions about what to test next.

## Roadmap

Near-term priorities:

- Add more literature sources for pasta, bread, pizza, and pastry.
- Expand texture validation beyond cooking loss.
- Add uncertainty/confidence scoring to more simulation outputs.
- Improve experiment ingestion and model retraining workflow.
- Make the frontend more useful for comparing candidates and saving trials.

Longer-term direction:

- Turn Glutenix into a practical formulation assistant for gluten-free experimentation.
- Support personal and small-lab recipe development.
- Make every prediction traceable to assumptions, data, and calibration coverage.

## Disclaimer

Glutenix is experimental software. It is not medical, nutritional, or regulatory advice. Gluten-free safety depends on ingredient sourcing, contamination control, process hygiene, and certified testing where required.
