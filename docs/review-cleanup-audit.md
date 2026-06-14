# Audit review-cleanup

Data audit: 2026-06-14

Branch: `review-cleanup`

Stato test: `uv run pytest -q` passa con `29 passed, 2 warnings`.

Obiettivo del documento: rendere i fix successivi precisi e facili da applicare anche da modelli piccoli, evitando correzioni speculative o claim non verificati.

## Sintesi Esecutiva

| Priorita | Area | Problema | Stato |
| --- | --- | --- | --- |
| P0 | ML/GPR | `PhysicsGPR.load()` ricostruisce un `ExactGP` con training data dummy | Confermato a runtime |
| P1 | Baking | La griglia temporale avanza per `(n_time - 1) * dt` ma riporta il tempo finale completo | Confermato staticamente |
| P1 | Fermentation | Lo zucchero e' clippato solo nel RHS, non nello stato restituito | Confermato staticamente |
| P1 | Tests/DB | I test SQLite non abilitano `PRAGMA foreign_keys=ON` | Confermato staticamente |
| P1 | Git/Security | Sidecar SQLite WAL/SHM non ignorati | Confermato staticamente |
| P2 | DB | `ondelete` non aggiorna database SQLite gia' creati | Confermato staticamente |
| P2 | DB/Schemas | Validazioni Pydantic non replicate con constraint DB | Confermato staticamente |
| P2 | Baking | Stabilita' esplicita considera poco il termine convettivo al bordo | Confermato staticamente |
| P2 | Packaging | `torch` usato direttamente ma non dichiarato come dipendenza diretta | Confermato staticamente |

## Cose Da Non Dire Piu'

Questi punti sono stati verificati e alcune affermazioni precedenti erano imprecise.

| Claim da evitare | Verita' verificata |
| --- | --- |
| "I test toccano ancora `glutenix.db` di produzione" | I test attuali usano SQLite in-memory. Il rischio resta in `train_model()` e negli import futuri, non nei test correnti. |
| "La BC convettiva in baking e' sicuramente sbagliata per il fattore 2" | Il fattore `2` e' coerente con un controllo a mezza cella superficie-centro. Il problema reale e' documentare la geometria e includere stabilita' al bordo. |
| "La divisione per zero nella gelatinizzazione baking esiste ancora" | Il range zero e' gestito. Il bug rimasto e' accettare range invertito come step function. |
| "`yield_coeff <= 0` non e' validato" | Ora e' validato in `glutenix/engine/fermentation.py:49-52`. |
| "Il bug `if ing.starch_pct` esiste ancora in amylose" | Ora usa `is not None` in `glutenix/engine/blend.py:118`. |
| "`torch.load(weights_only=True)` e' insicuro come pickle classico" | E' la scelta piu' sicura per questo checkpoint, ma servono `map_location`, validazione schema e limite di fiducia sui file caricati. |

## P0 - GPR Save/Load Rotto

File: `glutenix/ml/gpr.py`

Riferimenti: `glutenix/ml/gpr.py:162-192`

### Problema

`PhysicsGPR.save()` salva state dict e statistiche di normalizzazione, ma non salva i training input/target del modello `ExactGP`.

`PhysicsGPR.load()` crea:

```python
dummy_x = torch.zeros(1, n_features)
dummy_y = torch.zeros(1)
gpr.model = PhysicsGPModel(dummy_x, dummy_y, gpr.likelihood)
```

Un `ExactGP` usa i training data interni per il posterior predittivo. Dopo il load, il modello e' condizionato su un punto finto, non sul dataset reale.

### Prova

Verifica runtime eseguita:

```text
mean_max_diff 0.36405542492866516
std_max_diff 0.0705878734588623
```

Le predizioni prima/dopo `save/load` non coincidono.

### Fix Preciso

In `PhysicsGPR.save()` aggiungere al checkpoint:

```python
"train_x": self.model.train_inputs[0].detach().cpu(),
"train_y": self.model.train_targets.detach().cpu(),
```

In `PhysicsGPR.load()` caricare cosi':

```python
checkpoint = torch.load(path, map_location="cpu", weights_only=True)
required = {
    "model_state_dict",
    "likelihood_state_dict",
    "x_mean",
    "x_std",
    "y_mean",
    "y_std",
    "train_x",
    "train_y",
}
missing = required - checkpoint.keys()
if missing:
    raise ValueError(f"Invalid checkpoint, missing keys: {missing}")

gpr = cls()
gpr._x_mean = checkpoint["x_mean"]
gpr._x_std = checkpoint["x_std"]
gpr._y_mean = checkpoint["y_mean"]
gpr._y_std = checkpoint["y_std"]

gpr.likelihood = gpytorch.likelihoods.GaussianLikelihood()
gpr.model = PhysicsGPModel(checkpoint["train_x"], checkpoint["train_y"], gpr.likelihood)
gpr.model.load_state_dict(checkpoint["model_state_dict"])
gpr.likelihood.load_state_dict(checkpoint["likelihood_state_dict"])
gpr.model.eval()
gpr.likelihood.eval()
return gpr
```

### Test Da Aggiungere

File: `tests/test_gpr.py`

```python
def test_gpr_save_load_roundtrip(db_session, tmp_path):
    ingredients = db_session.query(Ingredient).all()
    train_x, train_y = generate_synthetic_data(ingredients, n_samples=50)

    gpr = PhysicsGPR()
    gpr.train(train_x, train_y, n_iter=20, verbose=False)

    before_mean, before_std = gpr.predict_batch(train_x[:5])

    path = tmp_path / "gpr.pt"
    gpr.save(str(path))
    loaded = PhysicsGPR.load(str(path))

    after_mean, after_std = loaded.predict_batch(train_x[:5])

    torch.testing.assert_close(after_mean, before_mean)
    torch.testing.assert_close(after_std, before_std)
```

## P1 - Normalizzazione GPR Con Un Solo Campione

File: `glutenix/ml/gpr.py`

Riferimenti: `glutenix/ml/gpr.py:65-80`

### Problema

`torch.std()` usa default unbiased/correction. Con un solo campione puo' produrre `nan`; `clamp(min=1e-8)` non corregge i `nan`.

### Fix Preciso

Sostituire:

```python
std = x.std(0).clamp(min=1e-8)
y_std = train_y.std().clamp(min=1e-8)
```

con:

```python
std = x.std(0, unbiased=False).clamp(min=1e-8)
y_std = train_y.std(unbiased=False).clamp(min=1e-8)
```

Opzionale: rifiutare training set troppo piccoli con `ValueError` se `train_x.shape[0] < 2`.

## P1 - Baking Time Grid Off By One

File: `glutenix/engine/baking.py`

Riferimenti: `glutenix/engine/baking.py:55-84`

### Problema

Il codice calcola:

```python
dt = total_time / n_time
t = np.linspace(0, total_time, n_time)
for n in range(n_time - 1):
```

Quindi il campo termico viene avanzato per `(n_time - 1) * dt`, ma l'array tempo ritorna fino al tempo totale.

### Fix Preciso

Usare `n_steps` per gli update e `n_steps + 1` per gli stati salvati:

```python
total_s = p.baking_time_min * 60.0
if dt_suggested > dt_max:
    n_steps = int(np.ceil(total_s / dt_max))
else:
    n_steps = p.n_time

dt = total_s / n_steps
t = np.linspace(0, total_s, n_steps + 1)
T = np.full((n_steps + 1, p.n_spatial), T0)

for n in range(n_steps):
    T_curr = T[n]
    ...
    T[n + 1] = T_next
```

Aggiornare anche `M = np.zeros(n_steps + 1)` e il loop Maillard.

## P1 - Fermentation Sugar Clipping Incompleto

File: `glutenix/engine/fermentation.py`

Riferimenti: `glutenix/engine/fermentation.py:54-80`

### Problema

Il RHS fa:

```python
S = max(S, 0.0)
```

ma il risultato restituito usa:

```python
sugar = sol.y[1]
```

Se il solver overshoota sotto zero, lo stato restituito puo' ancora contenere zucchero negativo.

### Fix Preciso

Applicare tre correzioni minime:

```python
if p.initial_sugar < 0:
    raise ValueError("initial_sugar must be non-negative")
if p.Km <= 0:
    raise ValueError("Km must be positive")
if p.yeast_conc < 0:
    raise ValueError("yeast_conc must be non-negative")
```

Dopo `solve_ivp`:

```python
if not sol.success:
    raise RuntimeError(f"Fermentation solver failed: {sol.message}")

co2_produced = np.minimum(sol.y[0], p.initial_sugar * p.yield_coeff)
sugar = np.maximum(sol.y[1], 0.0)
```

Migliore ma leggermente piu' invasivo: aggiungere un event terminale quando `S == 0`.

### Test Da Aggiungere

File: `tests/test_engine.py`

```python
def test_fermentation_rejects_invalid_yield_coeff():
    sim = FermentationSimulator(FermentationParams(yield_coeff=0.0))
    with pytest.raises(ValueError):
        sim.simulate()

def test_fermentation_sugar_non_negative():
    result = FermentationSimulator().simulate(duration_min=1000.0)
    assert np.all(result.sugar >= 0.0)
```

## P1 - Test SQLite Senza Foreign Keys

File: `tests/conftest.py`, `tests/test_gpr.py`

Riferimenti: `tests/conftest.py:10-13`, `tests/test_gpr.py:13-22`, `glutenix/db/base.py:10-14`

### Problema

La produzione abilita:

```python
PRAGMA foreign_keys=ON
```

I test in-memory no. Quindi i test possono non intercettare problemi su cascade, `SET NULL` e integrita' referenziale.

### Fix Preciso

Centralizzare una fixture test engine:

```python
from sqlalchemy import create_engine, event

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = sessionmaker(engine)()
    yield session
    session.close()
```

Poi rimuovere la fixture duplicata in `tests/test_gpr.py` e usare quella globale.

## P1 - Sidecar SQLite Non Ignorati

File: `.gitignore`

Riferimenti: `.gitignore:22-24`

### Problema

Sono ignorati `*.db` e `*.sqlite3`, ma non i sidecar WAL/SHM. Nel workspace possono apparire `glutenix.db-wal` e `glutenix.db-shm`.

### Fix Preciso

Aggiungere:

```gitignore
*.db-*
*.sqlite3-*
```

## P2 - `ondelete` Non Migra Database Esistenti

File: `glutenix/db/models.py`, `glutenix/config.py`

Riferimenti: `glutenix/db/models.py:67-147`, `glutenix/config.py:4-6`

### Problema

Il metadata SQLAlchemy ora include `ondelete`, ma `Base.metadata.create_all()` non modifica FK gia' esistenti in `glutenix.db`.

### Fix Preciso

Per dev semplice: documentare che dopo questi cambi serve ricreare il DB locale.

Comando manuale consigliato solo se si accetta di perdere dati dev:

```powershell
Remove-Item -LiteralPath "glutenix.db", "glutenix.db-wal", "glutenix.db-shm" -ErrorAction SilentlyContinue
uv run python -c "from glutenix.db.base import Base, engine; from glutenix.db.seed import seed_database; Base.metadata.create_all(engine); seed_database()"
```

Per progetto serio: introdurre Alembic prima di avere dati reali.

## P2 - Relazioni ORM E Delete Di Ingredient

File: `glutenix/db/models.py`

Riferimenti: `glutenix/db/models.py:39`, `glutenix/db/models.py:95-103`

### Problema

`BlendIngredient.ingredient_id` ha `ondelete="CASCADE"`, ma `Ingredient.blends` non ha `passive_deletes=True`. SQLAlchemy puo' tentare di settare `ingredient_id = NULL`, violando `nullable=False`, invece di lasciare lavorare il DB.

### Fix Preciso

Modificare:

```python
blends: Mapped[list["BlendIngredient"]] = relationship(back_populates="ingredient")
```

in:

```python
blends: Mapped[list["BlendIngredient"]] = relationship(
    back_populates="ingredient",
    passive_deletes=True,
)
```

Aggiungere test con FK attive che cancelli un `Ingredient` associato e verifichi il comportamento desiderato.

## P2 - Constraint DB Mancanti

File: `glutenix/db/models.py`, `glutenix/schemas/models.py`

Riferimenti: `glutenix/db/models.py:14-36`, `glutenix/db/models.py:98-103`, `glutenix/schemas/models.py:48-64`

### Problema

Pydantic valida categoria, percentuali e proporzioni, ma inserimenti ORM diretti possono bypassare tutto.

### Fix Preciso

Aggiungere in `models.py`:

```python
from sqlalchemy import CheckConstraint, UniqueConstraint
```

Per `Ingredient`:

```python
__table_args__ = (
    CheckConstraint("category in ('flour', 'starch', 'hydrocolloid')", name="ck_ingredient_category"),
    CheckConstraint("protein_pct is null or (protein_pct >= 0 and protein_pct <= 100)", name="ck_ingredient_protein_pct"),
    ...
)
```

Per `BlendIngredient`:

```python
__table_args__ = (
    CheckConstraint("proportion > 0 and proportion <= 1", name="ck_blend_ingredient_proportion"),
    UniqueConstraint("blend_id", "ingredient_id", name="uq_blend_ingredient"),
)
```

In `BlendCreate.proportions_sum_to_one()` aggiungere check duplicati:

```python
ids = [i.ingredient_id for i in self.ingredients]
if len(ids) != len(set(ids)):
    raise ValueError("Duplicate ingredient_id values are not allowed")
```

## P2 - JSON String Non Validati

File: `glutenix/schemas/models.py`, `glutenix/db/models.py`

Riferimenti: `glutenix/schemas/models.py:75-100`, `glutenix/db/models.py:119-127`, `glutenix/db/models.py:145-153`

### Problema

`results`, `metrics`, `parameters`, `conditions`, `target_properties` sono stringhe libere. La futura API potrebbe salvare JSON invalido.

### Fix Preciso

Opzione minima: aggiungere validator JSON sulle stringhe.

Opzione migliore: usare tipi Pydantic `dict[str, Any]` negli schema e serializzare centralmente quando si salva su DB.

Esempio minimo:

```python
import json
from pydantic import field_validator

@field_validator("results")
@classmethod
def valid_results_json(cls, value):
    json.loads(value)
    return value
```

Applicare anche a `metrics`, `parameters`, `conditions`, `target_properties`.

## P2 - ID Schema Non Validati

File: `glutenix/schemas/models.py`

Riferimenti: `glutenix/schemas/models.py:75-93`

### Problema

`SimulationResultCreate.blend_id`, `ExperimentResultCreate.blend_id` e `application_id` accettano valori negativi o zero.

### Fix Preciso

```python
blend_id: int = Field(gt=0)
application_id: Optional[int] = Field(None, gt=0)
```

Applicare anche a `BlendCreate.application_id`.

## P2 - Baking Stabilita' Al Bordo E Parametri Non Validati

File: `glutenix/engine/baking.py`

Riferimenti: `glutenix/engine/baking.py:49-69`

### Problema

La stabilita' esplicita usa solo:

```python
dt_max = 0.4 * dx_m**2 / alpha
```

Questo copre l'interno, ma il bordo convettivo dipende anche da `h`, `rho`, `cp`, `dx`.

### Fix Preciso

Validare parametri all'inizio di `simulate()`:

```python
if p.n_spatial < 2:
    raise ValueError("n_spatial must be >= 2")
if p.dough_thickness_cm <= 0:
    raise ValueError("dough_thickness_cm must be positive")
if p.thermal_diffusivity <= 0:
    raise ValueError("thermal_diffusivity must be positive")
if p.density <= 0 or p.specific_heat <= 0:
    raise ValueError("density and specific_heat must be positive")
if p.surface_heat_transfer < 0:
    raise ValueError("surface_heat_transfer must be non-negative")
```

Calcolare limite piu' conservativo:

```python
rho_cp = p.density * p.specific_heat
dt_int = 0.5 * dx_m**2 / alpha
dt_bc = 0.5 / (alpha / dx_m**2 + h / (rho_cp * dx_m))
dt_max = 0.8 * min(dt_int, dt_bc)
```

## P2 - Baking Maillard Threshold E Modello Arrhenius

File: `glutenix/engine/baking.py`

Riferimenti: `glutenix/engine/baking.py:92-98`

### Problema

Il Maillard parte a `T_surface > 373.15 K`, cioe' 100 C. Per browning reale e' piu' ragionevole usare circa 120-140 C, dipendente da water activity.

La formula usa `T_c + 200.0` invece di Kelvin in modo fisicamente standard.

### Fix Preciso

Aggiungere parametri in `BakingParams`:

```python
maillard_threshold_c: float = 140.0
maillard_A: float = 1e-4
maillard_Ea: float = 50_000.0
gas_constant: float = 8.314
```

Nel loop:

```python
T_surface_k = T[n, 0]
T_surface_c = T_surface_k - 273.15
if T_surface_c >= p.maillard_threshold_c:
    M[n] = M[n - 1] + dt * p.maillard_A * np.exp(
        -p.maillard_Ea / (p.gas_constant * T_surface_k)
    )
else:
    M[n] = M[n - 1]
```

## P2 - Baking Gelatinization Range Invertito

File: `glutenix/engine/baking.py`

Riferimenti: `glutenix/engine/baking.py:86-90`

### Problema

Se `gelatinization_temp_max < gelatinization_temp_min`, il codice lo tratta come step function. Meglio rigettare input invertiti.

### Fix Preciso

```python
if gelatinization_temp_max < gelatinization_temp_min:
    raise ValueError("gelatinization_temp_max must be >= gelatinization_temp_min")
elif gelatinization_temp_max == gelatinization_temp_min:
    G = np.where(T >= T_gel_min, 1.0, 0.0)
else:
    G = np.clip((T - T_gel_min) / (T_gel_max - T_gel_min), 0, 1)
```

## P2 - Blend Starchless Defaults Fuorvianti

File: `glutenix/engine/blend.py`

Riferimenti: `glutenix/engine/blend.py:17-20`, `glutenix/engine/blend.py:91-124`

### Problema

Per blend senza amido, `BlendProperties` mantiene default:

```python
gelatinization_temp_min = 65.0
gelatinization_temp_max = 75.0
amylose_pct = 20.0
```

Questi valori sono fuorvianti se `starch_pct == 0`.

### Fix Preciso

Opzione minima senza cambiare schema: usare `float("nan")` quando `props.starch_pct <= 0`.

Opzione migliore ma piu' invasiva: rendere i campi opzionali:

```python
gelatinization_temp_min: float | None = None
gelatinization_temp_max: float | None = None
amylose_pct: float | None = None
```

Poi aggiornare GPR feature generation per sostituire `None` con valore sentinel o imputazione esplicita.

## P2 - Seed Session Transaction Ownership

File: `glutenix/db/seed.py`

Riferimenti: `glutenix/db/seed.py:11-28`

### Problema

`seed_database(session=...)` non chiude piu' la session del chiamante, ma fa comunque `commit()` o `rollback()` sulla transazione del chiamante.

### Fix Preciso

Fare commit/rollback solo se la funzione possiede la session:

```python
def seed_database(session=None, commit: bool | None = None):
    owns_session = session is None
    if session is None:
        session = SessionLocal()
    if commit is None:
        commit = owns_session

    try:
        _seed_ingredients(session)
        _seed_applications(session)
        if commit:
            session.commit()
        else:
            session.flush()
    except Exception:
        if commit:
            session.rollback()
        raise
    finally:
        if owns_session:
            session.close()
```

## P2 - Seed Idempotency Troppo Grossolana

File: `glutenix/db/seed.py`

Riferimenti: `glutenix/db/seed.py:31-34`, `glutenix/db/seed.py:217-220`

### Problema

Se esiste anche un solo ingrediente, `_seed_ingredients()` salta tutto. Fix ai dati seed non aggiornano DB gia' creati.

### Fix Preciso

Definire liste dati seed come costanti e fare upsert per `name`.

Fix minimo: inserire i mancanti invece di saltare tutto:

```python
existing = {name for (name,) in session.query(Ingredient.name).all()}
session.add_all([ing for ing in ingredients if ing.name not in existing])
```

## P2 - Config Database Non Env-Overridable

File: `glutenix/config.py`

Riferimenti: `glutenix/config.py:1-6`

### Problema

Il DB e' sempre `PROJECT_ROOT / "glutenix.db"`. Non e' ideale per test, deploy o dati fuori dal source tree.

### Fix Preciso

```python
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_URL = os.getenv("GLUTENIX_DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'glutenix.db'}")
```

Nei test, impostare `GLUTENIX_DATABASE_URL` o continuare a creare engine in-memory dedicati.

## P2 - Packaging: Torch Non Dichiarato Direttamente

File: `pyproject.toml`

Riferimenti: `pyproject.toml:7-13`

### Problema

Il codice importa `torch` direttamente, ma `torch` arriva solo transitivamente da `gpytorch`. Questa e' una dipendenza implicita fragile.

### Fix Preciso

Aggiungere a `[project].dependencies`:

```toml
"torch>=2.0",
```

Se vuoi evitare install CUDA pesanti in CI Linux, decidere policy CPU-only prima di fissare versione/index.

## P3 - Test Lenti/Brittle GPR

File: `tests/test_gpr.py`

Riferimenti: `tests/test_gpr.py:25-51`

### Problema

Il test addestra un ExactGP con `300` samples e `100` iterazioni. Funziona ora, ma e' pesante e numericamente fragile.

### Fix Preciso

Ridurre il test unitario:

```python
train_x, train_y = generate_synthetic_data(ingredients, n_samples=80)
gpr.train(train_x, train_y, n_iter=30, verbose=False)
```

Spostare test piu' pesanti sotto marker `slow`.

## P3 - CI E Qualita'

File: repository root

### Problema

Non e' presente una workflow CI `.github/workflows/*`. Manca soglia coverage, lint e type check.

### Fix Preciso

Aggiungere CI minima:

```yaml
name: test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --locked --all-groups
      - run: uv run pytest
```

## Ordine Consigliato Dei Fix

1. Fixare `PhysicsGPR.save/load()` e aggiungere roundtrip test.
2. Abilitare FK nei test SQLite e aggiungere test cascade/SET NULL.
3. Correggere time grid baking off-by-one.
4. Correggere sugar clipping e validazioni `FermentationParams`.
5. Aggiornare `.gitignore` per sidecar SQLite.
6. Aggiungere constraint DB e validator schema mancanti.
7. Rendere `DATABASE_URL` env-overridable.
8. Aggiungere `torch` come dipendenza diretta.
9. Ridurre test GPR o marcarlo `slow`.
10. Aggiungere CI minima.

## Comandi Di Verifica

Eseguire dopo i fix principali:

```powershell
uv run pytest -q
```

Per verificare roundtrip GPR:

```powershell
uv run pytest tests/test_gpr.py -q
```

Per verificare che i test non aprano il DB di produzione, aggiungere una guardia autouse futura oppure eseguire un test dedicato che monkeypatchi aperture a `glutenix.db`.
