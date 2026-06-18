# Flavor Heuristic Model

Glutenix uses a documented heuristic flavor model to rank blends before running lab trials. The goal is not to replace sensory testing; the goal is to filter thousands of possible formulations down to a smaller set that is plausible functionally and sensorially.

## Scope

The model estimates flavor similarity from ingredient identity and blend proportions. It does not simulate fermentation aroma chemistry, Maillard reaction products, volatile loss, toppings, salt, fat additions, or human preference directly.

## Flavor Vector

Each ingredient is represented by eight sensory dimensions from 0 to 1:

- `neutral`: blandness or low flavor impact.
- `cereal`: wheat-like/cereal grain note.
- `nutty`: nut, seed, almond, toasted nut character.
- `earthy`: earthy, bran-like, buckwheat/teff/psyllium style note.
- `bitter`: bitter or astringent note.
- `sweet`: intrinsic mild sweetness.
- `toasted`: baked/roasted cereal character.
- `rich`: fatty, rounded, indulgent perception.

The blend profile is a weighted average of ingredient profiles.

## Application Targets

Application targets describe the desired sensory direction:

- `Pizza`: mild cereal flavor, moderate toasted note, low bitterness and earthiness.
- `Pane`: clean cereal note, moderate baked character, low bitterness.
- `Lievitati dolci`: more sweet/rich notes allowed, low earthy and bitter notes.
- `Frolla` / `Biscotti`: richer nutty/toasted profile is acceptable.
- `Pasta fresca`: neutral clean cereal flavor, very low toasted/bitter/earthy profile.

The score is computed from Euclidean distance between the blend flavor vector and target vector, transformed with a Gaussian kernel.

## Evidence Level

All current flavor profiles are `heuristic`.

They are based on common sensory descriptions in cereal science and gluten-free product development, plus practical expectations for the listed ingredients. They are not calibrated with a trained sensory panel or GC-MS volatile measurements yet.

## Calibration Path

1. Collect sensory ratings for ingredient slurries or simple baked bases.
2. Use a small panel with the same eight dimensions.
3. Update ingredient flavor vectors from average panel scores.
4. Run product trials for top candidates and record acceptability.
5. Fit application target vectors and sigma values against measured preference.

## Current Use In Optimization

`POST /optimize/application-suggest` combines three scores:

- `process_score`: fermentation/baking process match.
- `blend_score`: functional blend property match.
- `flavor_score`: sensory proxy match.

Default total score:

```text
0.55 * process_score + 0.25 * blend_score + 0.20 * flavor_score
```

This lets Glutenix rank blends that are physically plausible, application-appropriate, and less likely to have undesirable flavor before manual lab work.
