# Application Target Profiles Research

Scopo: definire range e vincoli realistici per generare i top N blend piu adatti a un utilizzo specifico: pizza, pane, biscotti, crostata/frolla, pasta fresca e lievitati dolci.

Questo documento non e ancora una fonte normativa. E una traccia di lavoro per raccogliere letteratura, trasformarla in target numerici e poi implementare un `Application Target Optimizer` in Glutenix.

## Obiettivo Prodotto

Dato un utilizzo, il sistema deve proporre blend ordinati per utilita.

Esempio input:

```json
{
  "application": "pizza",
  "ingredient_ids": [1, 4, 10, 11, 15],
  "top_n": 10,
  "n_samples": 10000
}
```

Esempio output:

```json
{
  "application": "Pizza",
  "candidates": [
    {
      "rank": 1,
      "score": 0.91,
      "proportions": {
        "White rice flour": 0.42,
        "Tapioca starch": 0.28,
        "Sorghum flour": 0.27,
        "Psyllium husk": 0.03
      },
      "properties": {
        "protein_pct": 6.8,
        "starch_pct": 76.2,
        "fiber_pct": 4.1,
        "water_absorption": 1.55,
        "viscosity_index": 1.9,
        "kcal_per_100g": 361
      },
      "simulation": {
        "volume_increase_pct": 64.2,
        "core_temp_c": 94.1,
        "crust_temp_c": 162.0
      },
      "notes": [
        "Buona espansione",
        "Idrocolloidi nel range target",
        "Assorbimento acqua compatibile con impasto pizza"
      ]
    }
  ]
}
```

## Metriche Target

Le metriche vanno divise in tre gruppi.

### 1. Metriche del Blend

- `protein_pct`: struttura, colore, valore nutrizionale.
- `starch_pct`: struttura, gelatinizzazione, friabilita.
- `fat_pct`: morbidezza, friabilita, shelf-life, gusto.
- `fiber_pct`: acqua legata, volume, valore nutrizionale.
- `water_absorption`: idratazione richiesta.
- `gelatinization_temp_min/max`: comportamento in cottura.
- `amylose_pct`: retrogradazione, struttura, croccantezza.
- `viscosity_index`: proxy interno per viscosita/tenuta gas.
- `hydrocolloid_pct`: struttura e ritenzione gas.

### 2. Metriche di Processo

- `fermentation_temp_c`
- `fermentation_duration_min`
- `baking_temp_c`
- `baking_duration_min`
- `dough_hydration_pct`, da aggiungere in futuro.
- `resting_time_min`, da aggiungere in futuro.

### 3. Metriche di Output

- `volume_increase_pct`
- `core_temp_c`
- `crust_temp_c`
- `gelatinization_reached`
- `predicted_quality_score`, da definire.
- `prediction_std`, incertezza del GPR.

## Range Iniziali Da Validare

I range sotto sono ipotesi operative per iniziare. Vanno validati con fonti scientifiche e prove sperimentali.

### Pizza Gluten-Free

Obiettivo: impasto estensibile, buona ritenzione gas, cornicione sviluppato, base non gommosa.

| Metrica | Range iniziale | Note |
|---|---:|---|
| `volume_increase_pct` | 45 - 85 | Volume alto ma non collasso. |
| `water_absorption` | 1.2 - 1.9 | Impasti GF pizza spesso richiedono piu acqua. |
| `viscosity_index` | 1.4 - 2.8 | Tenuta gas senza impasto troppo gommoso. |
| `hydrocolloid_pct` | 1.0% - 4.0% | Psyllium/xanthan/HPMC da validare per tipo. |
| `fiber_pct` | 2% - 8% | Troppa fibra puo appesantire. |
| `fat_pct` | 0.5% - 6% | Grassi moderati. |
| `core_temp_c` | 90 - 98 | Gelatinizzazione e struttura interna. |

Vincoli ingredienti iniziali:

- Farine: 50% - 85%
- Amidi: 10% - 45%
- Idrocolloidi: 1% - 4%
- Farine grasse come mandorla: max 10% per pizza classica

### Pane Gluten-Free

Obiettivo: volume alto, mollica morbida, buona shelf-life, struttura non friabile.

| Metrica | Range iniziale | Note |
|---|---:|---|
| `volume_increase_pct` | 60 - 110 | Piu alto della pizza. |
| `water_absorption` | 1.4 - 2.2 | Impasto/pastella piu idratato. |
| `viscosity_index` | 1.8 - 3.5 | Ritenzione gas importante. |
| `hydrocolloid_pct` | 1.5% - 5.0% | HPMC/psyllium spesso utili. |
| `fiber_pct` | 3% - 10% | Migliora acqua/shelf-life ma puo ridurre volume. |
| `protein_pct` | 5% - 12% | Struttura e nutrizione. |
| `core_temp_c` | 94 - 99 | Cottura completa. |

Vincoli ingredienti iniziali:

- Farine: 45% - 80%
- Amidi: 15% - 45%
- Idrocolloidi: 1.5% - 5%
- Farine integrali/pseudocereali: 10% - 50%

### Biscotti Gluten-Free

Obiettivo: friabilita, croccantezza, basso sviluppo, buona tenuta forma.

| Metrica | Range iniziale | Note |
|---|---:|---|
| `volume_increase_pct` | 0 - 25 | Il volume alto non e desiderato. |
| `water_absorption` | 0.7 - 1.4 | Impasto piu asciutto. |
| `viscosity_index` | 0.5 - 1.4 | Bassa elasticita. |
| `hydrocolloid_pct` | 0% - 1.5% | Troppi idrocolloidi rendono gommoso. |
| `fat_pct` | 5% - 25% | Friabilita e gusto. |
| `starch_pct` | 45% - 80% | Croccantezza e struttura. |
| `fiber_pct` | 1% - 8% | Troppa fibra puo indurire. |

Vincoli ingredienti iniziali:

- Farine: 50% - 90%
- Amidi: 0% - 35%
- Idrocolloidi: 0% - 1.5%
- Mandorla/frutta secca: 0% - 40% a seconda dello stile

### Crostata / Frolla Gluten-Free

Obiettivo: friabilita, tenuta forma, bassa elasticita, non collassare in cottura.

| Metrica | Range iniziale | Note |
|---|---:|---|
| `volume_increase_pct` | 0 - 15 | Espansione non desiderata. |
| `water_absorption` | 0.7 - 1.3 | Bassa idratazione. |
| `viscosity_index` | 0.5 - 1.2 | Struttura corta, non elastica. |
| `hydrocolloid_pct` | 0% - 1.0% | Solo se serve tenuta. |
| `fat_pct` | 8% - 30% | Friabilita. |
| `starch_pct` | 45% - 75% | Corpo e croccantezza. |
| `protein_pct` | 4% - 12% | Troppo alto puo indurire. |

Vincoli ingredienti iniziali:

- Farine: 60% - 95%
- Amidi: 0% - 30%
- Idrocolloidi: 0% - 1%
- Mandorla: 0% - 35%

### Pasta Fresca Gluten-Free

Obiettivo: coesione, tenuta in cottura, elasticita moderata, non collosa.

| Metrica | Range iniziale | Note |
|---|---:|---|
| `water_absorption` | 0.9 - 1.6 | Dipende molto da uova/acqua. |
| `viscosity_index` | 1.2 - 2.5 | Serve coesione ma non gommosita. |
| `hydrocolloid_pct` | 0.5% - 3.0% | Per tenuta e laminazione. |
| `protein_pct` | 7% - 15% | Struttura. |
| `starch_pct` | 50% - 80% | Corpo. |
| `amylose_pct` | 15% - 30% | Tenuta e retrogradazione. |

Vincoli ingredienti iniziali:

- Farine: 60% - 95%
- Amidi: 0% - 30%
- Idrocolloidi: 0.5% - 3%

### Lievitati Dolci Gluten-Free

Obiettivo: volume alto, morbidezza, umidita, struttura non gommosa.

| Metrica | Range iniziale | Note |
|---|---:|---|
| `volume_increase_pct` | 70 - 130 | Alta espansione. |
| `water_absorption` | 1.3 - 2.1 | Impasti ricchi e idratati. |
| `viscosity_index` | 1.6 - 3.2 | Ritenzione gas. |
| `hydrocolloid_pct` | 1.0% - 4.5% | Struttura e morbidezza. |
| `fat_pct` | 3% - 15% | Formula completa includera grassi aggiunti. |
| `fiber_pct` | 2% - 8% | Acqua e shelf-life. |
| `core_temp_c` | 92 - 98 | Cottura completa senza asciugare. |

Vincoli ingredienti iniziali:

- Farine: 45% - 85%
- Amidi: 10% - 45%
- Idrocolloidi: 1% - 4.5%

## Fonti Da Cercare

Tipologie di fonti prioritarie:

- Review scientifiche su gluten-free bread, pizza, cookies, pasta.
- Studi su HPMC, xanthan, guar e psyllium in prodotti senza glutine.
- Studi su amidi: tapioca, potato, corn, rice starch e loro impatto su volume/texture.
- Studi su pseudocereali: sorghum, buckwheat, teff, quinoa, oat.
- Testi di baking science e cereal science.
- Database composizionali: USDA FoodData Central, CREA/food composition tables, EFSA quando utile.

Query utili:

- `gluten-free bread hydrocolloids HPMC xanthan psyllium volume texture review`
- `gluten-free pizza dough hydrocolloid formulation rice tapioca starch`
- `gluten-free cookies flour blend starch fat texture hardness`
- `gluten-free shortcrust pastry formulation rice flour corn starch`
- `gluten-free pasta formulation hydrocolloid cooking loss firmness`
- `gluten-free bread water absorption dough rheology specific volume`
- `HPMC gluten-free bread specific volume crumb firmness`
- `psyllium gluten-free bread dough rheology volume`

## Fonti Verificate E Dati Estratti

Questa sezione contiene fonti reali gia individuate, con dati numerici utili per convertire letteratura in vincoli Glutenix.

### Pizza Gluten-Free: Dey et al. 2023

- Titolo: `Textural characteristics and color analyses of 3D printed gluten-free pizza dough and crust`
- Autori: Dey S, Maurya C, Hettiarachchy N, Seo HS, Zhou W.
- Journal: `Journal of Food Science and Technology`, 2023, 60(2):453-463.
- DOI: `10.1007/s13197-022-05596-w`
- PMCID: `PMC9873876`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC9873876/`

Dati estraibili:

| Dato | Valore |
|---|---:|
| Blend GF usato | sweet brown rice 30.9%, tapioca starch 25%, brown rice 19%, sorghum 25%, xanthan gum 0.1% |
| Formula dough GF | GF flour 41.6%, water 55.6%, oil 1.4%, yeast 0.3%, salt 0.3%, sugar 0.6%, emulsifier 0.2% |
| Formula wheat comparativa | wheat flour 50.0%, water 46.7%, oil 1.7%, yeast 0.3%, salt 0.4%, sugar 0.7%, emulsifier 0.2% |
| Fermentazione GF ottimale | 120 min at 37 C |
| Fermentazione wheat comparativa | 60 min at 37 C |
| Cottura ottimale | 10 min at 204.4 C |
| Water increase GF vs wheat | 55.6% vs 46.7% dough basis |
| GF baked crust hardness | 4546.21 +/- 19.57 |
| GF baked crust fracturability | 22.51 +/- 0.07 |
| GF baked crust springiness | 0.99 +/- 0.00 |
| GF baked crust cohesiveness | 0.93 +/- 0.01 |
| GF baked crust chewiness | 4167.14 +/- 51.99 |
| GF baked crust resilience | 0.544 +/- 0.01 |

Implicazioni per Glutenix:

- Per pizza GF, idratazione target piu alta rispetto a wheat: circa 55%-56% su formula totale, oppure ~133% water/flour considerando 200 mL acqua su 150 g farina nella procedura.
- Una base realistica per pizza e: riso/sorgo/tapioca + xanthan basso. Nel nostro database mancano arrowroot e sweet brown rice specifica, ma possiamo approssimare con sweet rice + rice + tapioca + sorghum.
- La fermentazione GF puo richiedere tempi piu lunghi della wheat pizza.

Confidenza: `high` per quella formula specifica; `medium` per generalizzazione a tutte le pizze GF.

### Pizza Gluten-Free Proteica: Pasqualone et al. 2022

- Titolo: `The Effectiveness of Extruded-Cooked Lentil Flour in Preparing a Gluten-Free Pizza with Improved Nutritional Features and a Good Sensory Quality`
- Autori: Pasqualone A, Costantini M, Faccia M, Difonzo G, Caponio F, Summo C.
- Journal: `Foods`, 2022, 11(3):482.
- DOI: `10.3390/foods11030482`
- PMCID: `PMC8834442`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC8834442/`

Formulazioni dough pizza, g/100 g dough:

| Ingrediente | Control | Native lentil | Extruded-cooked lentil |
|---|---:|---:|---:|
| Rice flour | 30 | 20 | 20 |
| Native lentil flour | 0 | 10 | 0 |
| Extruded-cooked lentil flour | 0 | 0 | 10 |
| Corn flour | 7.5 | 7.5 | 7.5 |
| Corn starch | 7.5 | 7.5 | 7.5 |
| Psyllium seed husk powder | 1.5 | 1.5 | 1.5 |
| HPMC | 1.0 | 0 | 0 |
| Yeast | 1.0 | 1.0 | 1.0 |
| Salt | 1.5 | 1.5 | 1.5 |
| Water | 50 | 48 | 53 |

Nutrizione pizza finita:

| Parametro | Control | Native lentil | Extruded-cooked lentil |
|---|---:|---:|---:|
| Moisture g/100g | 38.1 | 39.3 | 38.9 |
| Carbohydrates g/100g | 54.1 | 49.1 | 49.7 |
| Protein g/100g | 4.4 | 7.4 | 7.3 |
| Lipids g/100g | 0.1 | 0.3 | 0.3 |
| Fiber g/100g | 3.3 | 3.9 | 3.8 |
| Energy kcal/100g | 242 | 237 | 238 |

Altri dati:

- Extruded-cooked lentil flour initial viscosity: `69.3 BU`.
- L'uso di lentil flour al 10% dough basis ha aumentato proteine e fibra senza peggiorare l'accettabilita consumer rispetto al controllo.
- La farina di lenticchia estrusa ha permesso di eliminare HPMC nella formula sperimentale.

Implicazioni per Glutenix:

- Per pizza funzionale/proteica, legume flour intorno a 10% su dough basis e un punto di partenza realistico.
- Psyllium 1.5% su dough basis e una fonte concreta per vincolo pizza.
- HPMC 1% e usato nel controllo, ma puo essere sostituito da ingredienti pregelatinizzati/estrusi con proprieta idrocolloidali.

Confidenza: `high` per pizza rice/corn/lentil; `medium` per trasferimento ad altri legumi.

### Pane Gluten-Free: Parsamajd et al. 2025

- Titolo: `Synergistic Effects of Hydrocolloid Combinations on Gluten-Free Batter and Bread Characteristics`
- Autori: Parsamajd M, Fazaeli M, Majdinasab M, Golmakani MT.
- Journal: `Food Science & Nutrition`, 2025, 13(10):e71107.
- DOI: `10.1002/fsn3.71107`
- PMCID: `PMC12540201`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC12540201/`

Base formulation, percentuali su flour/starch basis:

| Ingrediente | Valore |
|---|---:|
| Rice flour | 25% |
| Quinoa flour | 10% |
| Corn starch | 15% |
| Tapioca starch | 15% |
| ADA modified starch | 5% |
| Corn flour | 30% |
| Water | 110% flour/starch basis |
| Margarine | 5% |
| Sugar | 3% |
| Salt | 1.5% |
| Sodium caseinate | 3% |
| SSL | 0.4% |
| Active dry yeast | 2% |
| Hydrocolloids | 2% total flour/starch basis |

Hydrocolloid treatments:

| Sample | HPMC | Guar | Xanthan |
|---|---:|---:|---:|
| Guar | 0 | 2 | 0 |
| HPMC | 2 | 0 | 0 |
| Xanthan | 0 | 0 | 2 |
| Xanthan-Guar | 0 | 1 | 1 |
| HPMC-Guar | 1 | 1 | 0 |
| HPMC-Xanthan | 1 | 0 | 1 |

Dati chiave:

| Dato | Valore |
|---|---:|
| Miglior combinazione riportata | HPMC-Xanthan |
| HPMC-Xanthan hardness | 1.31 N |
| HPMC-Xanthan cohesiveness | 0.78 |
| HPMC-Xanthan resilience | 0.45 |
| Moisture range breads | 52.72% - 55.38% |
| HPMC-Xanthan porosity | 36.04% |
| Peak gelatinization range | 108.61 C - 115.79 C |

Implicazioni per Glutenix:

- Per pane GF, hydrocolloid total al 2% flour/starch basis e un punto di partenza realistico.
- HPMC + xanthan 1:1 appare superiore a HPMC+guar per texture in questo sistema.
- Acqua al 110% flour/starch basis e realistica per bread batter GF.

Confidenza: `high` per pane rice/corn/quinoa/starch con idrocolloidi; `medium` per farine diverse.

### Pane Quinoa Gluten-Free: Ghodosipoor et al. 2025

- Titolo: `Optimization of Quinoa-Based Gluten-Free Bread Production Using Microbial Transglutaminase Enzyme and Hydroxypropyl Methyl Cellulose (HPMC) by Response Surface Methodology`
- Autori: Ghodosipoor Z, Zahed O, Fallahzadeh H, Mollakhalili-Meybodi N, Nematollahi A.
- Journal: `Food Science & Nutrition`, 2025, 13(9):e70891.
- DOI: `10.1002/fsn3.70891`
- PMCID: `PMC12400160`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC12400160/`

Design:

- TG range: `0% - 1.5% w/w`
- HPMC range: `0% - 2% w/w`
- Base: 100 g quinoa flour; sugar 10%, salt 1%, shortening 10%, active dry yeast 2.2%.
- Fermentation: 3 h at 29 C, then 30 min at 29 C and 85% RH.
- Baking: 25 min at 170 C.

Optimum RSM:

| Variabile/risposta | Valore |
|---|---:|
| TG optimum | 0.414% w/w |
| HPMC optimum | 1.283% w/w |
| Specific volume predicted | 2.320 cm3/g |
| Specific volume experimental | 2.339 +/- 0.05 cm3/g |
| Moisture experimental | 38.937 +/- 0.01% |
| Overall acceptability experimental | 7.512 +/- 0.17 |
| Hardness experimental | 5462.11 +/- 32.62 g |
| Quinoa control SV | 1.78 +/- 0.07 cm3/g |
| Wheat control SV | 2.91 +/- 0.13 cm3/g |
| Optimized GF SV improvement vs quinoa control | approx. +31.4% |

Implicazioni per Glutenix:

- HPMC ~1.3% e TG ~0.4% sono range concreti per bread-like GF con quinoa.
- Specific volume target realistico per pane GF sperimentale: circa 2.3 cm3/g, mentre wheat control nello studio e 2.9 cm3/g.
- Possiamo usare `specific_volume_cm3_g` come metrica futura piu robusta di `volume_increase_pct` per pane.

Confidenza: `high` per pane quinoa; `medium` per estensione ad altri pseudocereali.

### Biscotti Gluten-Free: Dadali et al. 2025

- Titolo: `Multifactorial Optimization of Gluten-Free Cookie With Artichoke Bracts as Rice Flour Substitute and Transglutaminase`
- Autori: Dadali C, Ozcan Y, Ensari IC.
- Journal: `Food Science & Nutrition`, 2025, 13(6):e70420.
- DOI: `10.1002/fsn3.70420`
- PMCID: `PMC12152272`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC12152272/`

Control formula:

| Ingrediente | Quantita |
|---|---:|
| Rice flour | 140.00 g |
| Sugar | 60.90 g |
| Margarine | 56.00 g |
| Water | 63.40 g |
| Skimmed milk powder | 1.40 g |
| Baking powder | 2.10 g |
| Salt | 1.75 g |

Design e optimum:

| Dato | Valore |
|---|---:|
| Rice flour substitute range | 0% - 30% |
| Transglutaminase range | 0% - 1% |
| Optimum artichoke bracts substitute | 18.65% |
| Optimum transglutaminase | 0.99% |
| Optimum fiber | 7.97 g/100g |
| Optimum antioxidant activity | 2.89 umol TE/g |
| Optimum total phenolic content | 0.74 mg GAE/g |
| Optimum hardness | 23.38 N |
| Optimum fracturability | 42.21 mm |

Dataset sperimentale utile:

- Artichoke 0%, TG 0%: hardness 17.74 N, spread ratio 5.56.
- Artichoke 30%, TG 0%: hardness 29.38 N, spread ratio 5.11.
- Artichoke 30%, TG 1%: hardness 27.19 N, overall acceptability 8.82.

Implicazioni per Glutenix:

- Per biscotti, un range realistico per sostituzioni fiber-rich e 0%-30% della farina di riso.
- Hardness target per biscotti GF accettabili, in questo setup, e circa 18-30 N.
- Spread ratio target osservato circa 5.1-5.9.
- Per biscotti, alto volume non e target: score deve premiare friabilita/spread/texture, non fermentazione.

Confidenza: `high` per cookie rice/artichoke/TG; `medium` per crostata/frolla.

### Pasta Fresca Gluten-Free: Lux et al. 2023

- Titolo: `Physical quality of gluten-free doughs and fresh pasta made of amaranth`
- Autori: Lux nee Bantleon T, Spillmann F, Reimold F, Erdos A, Lochny A, Floter E.
- Journal: `Food Science & Nutrition`, 2023, 11(6):3213-3223.
- DOI: `10.1002/fsn3.3301`
- PMCID: `PMC10261804`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC10261804/`

Design:

- Amaranth flour:water ratios tested: `1:2`, `1:4`, `1:6`, `1:8`, `1:10`.
- Sodium alginate: `1.0%` and `1.5%`.
- Dough heat treatment: `80 C`, `60 min`, `300 rpm`.
- Extrusion bath: `0.1 M calcium L-lactate pentahydrate`, approx. 20 C.
- Gel formation time: `30 min`.
- Cooking times tested: `5`, `10`, `15 min`.

Dati utili:

| Dato | Valore |
|---|---:|
| Amaranth gelatinization temperature cited | 62 - 68 C |
| k threshold problematic for extrusion | k > 200 Pa s^n |
| 1:2 dough k, 1.0% alginate | 295.51 Pa s^n |
| 1:2 dough k, 1.5% alginate | 320.51 Pa s^n |
| Cooking loss range observed | approx. 0.85 - 2.79 g/100g |
| Best structural indication | 1.5% alginate generally lower cooking loss / better shape retention |

Cooking loss examples:

| Ratio + alginate | 5 min | 10 min | 15 min |
|---|---:|---:|---:|
| 1:2, 1.0% alginate | 1.79 | 1.97 | 2.27 |
| 1:6, 1.0% alginate | 0.98 | 1.43 | 1.46 |
| 1:10, 1.5% alginate | 1.10 | 1.19 | 0.85 |

Implicazioni per Glutenix:

- Per pasta fresca GF, aggiungere metriche specifiche: `cooking_loss_pct`, `firmness_N`, `swelling_index`, `water_absorption_cooking`.
- Range buono iniziale per cooking loss: sotto 3 g/100g.
- Alginate non e ancora nel DB ingredienti: se vogliamo modellare pasta seriamente va aggiunto.

Confidenza: `high` per pasta amaranth/alginate; `medium` per pasta con altri pseudocereali.

### Pasta Gluten-Free Di Riso: Liu et al. 2026

- Titolo: `Synergistic effects of konjac glucomannan and curdlan on the qualities and starch digestibility of extruded gluten-free rice pasta`
- Autori: Liu Q, Zhang S, Lin C, et al.
- Journal: `Food Chemistry X`, 2026, 33:103403.
- DOI: `10.1016/j.fochx.2025.103403`
- PMCID: `PMC12769803`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC12769803/`

Design:

- High-amylose rice flour: starch 78.16%, amylose 28.12%.
- Konjac glucomannan (KGM): `6%` based on starch mass.
- Curdlan (CUD): `0%`, `1%`, `2%`, `3%` based on starch mass.
- Extrusion moisture: `32%`.
- Twin-screw extrusion temperatures: `50`, `80`, `75 C`.
- Feed speed: `10 kg/h`.
- Screw speed: `500 rpm`.

Dati utili:

| Dato | Valore |
|---|---:|
| KGM level | 6% starch basis |
| Curdlan tested | 1% - 3% starch basis |
| Best digestibility indication | CUD 3% gave minimum estimated glycemic index |
| Rice flour gelatinization peak Tp | approx. 75 C |
| RF peak viscosity | 2566 cP |
| RF + KGM + 3% CUD peak viscosity | 4349.67 cP |
| RF consistency K | 65.27 Pa s^n |
| RF + KGM + 3% CUD consistency K | 200.22 Pa s^n |

Implicazioni per Glutenix:

- Per pasta estrusa, KGM/curdlan sono ingredienti molto rilevanti ma non ancora in DB.
- `amylose_pct` e cruciale: questa fonte usa rice high-amylose con 28.12% amylose.
- Per pasta, non basta score su cottura: servono anche indice glicemico stimato o digestibilita se vogliamo prodotto funzionale.

Confidenza: `high` per pasta di riso estrusa con KGM/CUD; `low-medium` per pasta fresca non estrusa.

### Spaghetti Gluten-Free Di Riso Con SPI: Detchewa et al. 2016

- Titolo: `Preparation of gluten-free rice spaghetti with soy protein isolate using twin-screw extrusion`
- Autori: Detchewa P, Thongngam M, Jane JL, Naivikul O.
- Journal: `Journal of Food Science and Technology`, 2016, 53(9):3485-3494.
- DOI: `10.1007/s13197-016-2323-8`
- PMCID: `PMC5069250`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC5069250/`

Design:

- Base: dry-milled high-amylose rice flour CNT1 + waxy rice flour RD6 in ratio `90:10`.
- Soy protein isolate: `0%`, `2.5%`, `5.0%`, `7.5%`, `10.0%` dry basis.
- Twin-screw extrusion, moisture `32%`, screw speed `220 rpm`.
- Barrel temperatures: `40`, `70`, `95`, `95`, `95`, `80`, `70 C`.

Dati utili da Table 3:

| Sample | SPI % | Cooking time min | Cooking loss % | Water adsorption index % |
|---|---:|---:|---:|---:|
| GFRS-SPI0 | 0.0 | 17.6 | 25.4 | 246.2 |
| GFRS-SPI2.5 | 2.5 | 14.7 | 18.1 | 247.6 |
| GFRS-SPI5.0 | 5.0 | 13.7 | 17.0 | 248.1 |
| GFRS-SPI7.5 | 7.5 | 13.1 | 21.0 | 253.4 |
| GFRS-SPI10 | 10.0 | 13.1 | 21.8 | 254.3 |

Implicazioni per Glutenix:

- SPI ha effetto non lineare: migliora cooking loss fino a circa `5%`, poi l'eccesso peggiora la struttura.
- Il water adsorption index e molto piu alto rispetto ai record Liu/Lux e va trattato come metrica separata finche il modello non distingue scale/metodi.
- Questo paper e utile per validare la branca `dried_extruded` con proteine, non solo idrocolloidi.

Confidenza: `high` per spaghetti di riso estrusi con SPI; `low-medium` per pasta fresca non estrusa.

### Review Pane Gluten-Free: Alibekova et al. 2026

- Titolo: `Problems and Approaches in the Improvement of Gluten-Free Bread Texture: A Comprehensive Review`
- Autori: Alibekova Z, Bayisbayeva M, Shamsudin R, Bakhtybekova A, Alibekov R, Aimenov Z.
- Journal: `International Journal of Food Science`, 2026:5214023.
- DOI: `10.1155/ijfo/5214023`
- PMCID: `PMC13159086`
- URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC13159086/`

Range idrocolloidi riportati dalla review:

| Hydrocolloid | Recommended concentration | Main effect |
|---|---:|---|
| CMC | 0.5% - 1.5% | aumenta viscosita, migliora crumb |
| HPMC | 0.5% - 1.0% approx. | freschezza e gas retention |
| Pectin | 0.5% - 2.0% | softness/elasticity, lower GI |
| Beta-glucan | 1.0% - 3.0% | volume, moisture retention |
| Gum arabic | 1.5% - 3.0% | stabilita, softness, shelf-life |
| Gum tragacanth | 0.5% - 1.5% | gas retention |
| Xanthan + guar | 0.5% - 1.5% total | gas retention, volume, porosity |
| Guar gum | 0.5% - 1.0% | viscosita, gas bubble distribution |
| Psyllium | 1.0% - 2.5% | volume/elasticity; excess rubbery |
| Carob gum | 0.5% - 1.5% | smoother/more airy dough |

Note dalla review:

- HPMC a 0.5%-2.0% puo aumentare viscosity/gas-holding ma dosi alte possono dare crumb dense/sticky.
- Psyllium circa 5% flour weight e riportato come capace di aumentare specific volume 2-3x in alcuni esperimenti, ma il rischio e texture rubbery.
- Xanthan + guar puo aumentare specific loaf volume circa 10%-15% e ridurre hardness, ma dipende dalla formula.

Implicazioni per Glutenix:

- Questa review e utile per prior range generali, ma i valori vanno sempre collegati alla fonte originale quando possibile.
- Per il primo optimizer possiamo usare questi range come default con confidenza `medium`, poi raffinarli con paper specifici.

Confidenza: `medium` per range generali; `high` solo quando tracciamo al paper originale.

## Come Trasformare Letteratura In Vincoli

Per ogni paper o testo:

1. Estrarre prodotto target.
2. Estrarre ingredienti e percentuali.
3. Estrarre idratazione e processo.
4. Estrarre metriche misurate: specific volume, hardness, springiness, cooking loss, sensory score.
5. Convertire in feature Glutenix quando possibile.
6. Assegnare livello di confidenza: `low`, `medium`, `high`.
7. Annotare se il range e teorico, sperimentale o commerciale.

Template fonte:

```md
### Fonte

- Titolo:
- Autori:
- Anno:
- DOI/URL:
- Prodotto:
- Ingredienti:
- Processo:
- Metriche:
- Range estratti:
- Implicazione per Glutenix:
- Confidenza:
```

## Score Function MVP

Ogni candidato riceve uno score normalizzato 0-1.

```text
score = weighted_target_fit - uncertainty_penalty - constraint_penalty
```

Componenti:

- `target_fit`: quanto le metriche cadono nei range desiderati.
- `uncertainty_penalty`: penalizza alta deviazione standard del GPR.
- `constraint_penalty`: penalizza ingredienti o categorie fuori range.
- `nutrition_bonus`: opzionale, premia fibre/proteine o penalizza kcal/sodio in base all'applicazione.

## Roadmap Implementativa

1. Consolidare fonti e range in questo documento.
2. Aggiungere `ApplicationTargetProfile` in codice o DB.
3. Implementare score function configurabile.
4. Creare endpoint `POST /applications/{id}/suggest-blends`.
5. Aggiungere UI: scelta applicazione, ingredienti, top N, vincoli.
6. Salvare candidate e risultati per migliorare il GPR.
7. Validare con esperimenti reali.

## Domande Aperte

- Gli ingredienti extra-formula, come acqua, sale, zucchero, olio e lievito, devono entrare nel modello come variabili separate?
- I target devono essere per prodotto finito o per miscela secca?
- Per pizza/pane conviene usare specific volume invece di volume increase percent?
- Per biscotti/crostata servono metriche nuove: spread ratio, hardness, fracturability, crispness.
- Per pasta fresca servono metriche nuove: cooking loss, firmness, stickiness.
