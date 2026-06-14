# Glutenix — Simulatore e Ottimizzatore di Mix di Farine Senza Glutine

## Idea e Motivazione

Il problema della panificazione senza glutine è fondamentalmente un problema di **formulazione**: il glutine svolge decine di funzioni fisico-chimiche simultanee (struttura, elasticità, ritenzione dei gas, legame con l'acqua) e non esiste una singola farina che lo rimpiazzi. Il risultato corretto dipende dalla combinazione di più farine e addensanti, calibrata sull'applicazione specifica.

Il mercato attuale risolve questo problema con mix pre-confezionati generici ("mix per pane", "mix per dolci") che sono compromessi mediocri. Non esiste uno strumento pubblico che aiuti a capire **perché** un certo mix funziona per la pizza e non per un lievitato, o che suggerisca come ottimizzarlo.

Il progetto si ispira ad **Alchemix di Brembo Solutions** — un AI-powered recipe formulator per l'industria manifatturiera — applicato al dominio della panificazione GF. Come Alchemix, l'obiettivo non è sostituire l'esperimento fisico ma renderlo 10x più efficiente: escludere le combinazioni che non funzioneranno, guidare verso quelle promettenti, imparare da ogni risultato.

---

## Il Problema dei Dati (e come lo risolviamo)

Il vincolo principale di questo dominio è la **mancanza di dati pubblici strutturati**: le grandi aziende del settore (Schär, Caputo GF, Molino Dallagiovanna) hanno anni di test interni con misure fisiche e score, ma non li pubblicano perché sono il loro vantaggio competitivo. La letteratura scientifica esiste ma è frammentata, su scala di laboratorio, e non aggregabile facilmente.

Fare tutti gli esperimenti manualmente è impraticabile: lo spazio delle combinazioni possibili (10+ farine, proporzioni continue, additivi, idratazione, processo) è troppo grande rispetto al costo per campione.

La soluzione architetturale è un **sistema ibrido a doppia sorgente di conoscenza**:

| Sorgente | Fedeltà | Costo | Ruolo |
|---|---|---|---|
| Physics Engine | Bassa-Media | Zero | Esplora lo spazio, genera prior |
| Esperimento reale | Alta | Alto | Corregge il modello, valida |

Il Physics Engine usa equazioni fisico-chimiche note (cinetica di fermentazione, trasferimento di calore, gelatinizzazione dell'amido) per simulare il comportamento di un blend **senza dati sperimentali**. Non è perfetto, ma è gratis e permette di esplorare migliaia di combinazioni. Gli esperimenti reali vengono usati solo dove il modello è incerto — massimizzando l'informazione per ogni test fisico condotto.

Questo approccio si chiama **Multi-Fidelity Bayesian Optimization** ed è lo stato dell'arte per problemi di ottimizzazione con esperimenti costosi.

---

## Architettura del Sistema

```
┌─────────────────────────────────────────────┐
│                  UI Layer                    │
│         React + Plotly  /  Streamlit         │
└──────────────────┬──────────────────────────┘
                   │ HTTP
┌──────────────────▼──────────────────────────┐
│               API Layer (FastAPI)            │
│  /blend/simulate  /blend/optimize  /blend/score │
└──┬───────────────┬──────────────────────────┘
   │               │
┌──▼──────┐  ┌─────▼──────────────────────────┐
│   DB    │  │        Orchestrator             │
│         │  │  coordina il pipeline completo  │
│Postgres │  └──┬─────────────┬───────────────┘
│+SQLAlch.│     │             │
└──┬──────┘     │             │
   │       ┌────▼────┐  ┌─────▼──────┐
   │       │ Physics │  │  ML Layer  │
   │       │ Engine  │  │            │
   │       │         │  │  GPR /     │
   │       │ODE/PDE  │  │  BNN       │
   │       │SciPy    │  │  GPyTorch  │
   │       └────┬────┘  └─────┬──────┘
   │            │             │
   │       ┌────▼─────────────▼──────┐
   │       │   Multi-Fidelity BO     │
   │       │       BoTorch           │
   │       │  (ottimizza blend e     │
   │       │   suggerisce esperim.)  │
   │       └─────────────────────────┘
   │
   ├── ingredients (proprietà farine)
   ├── applications (profili target)
   ├── simulations (risultati physics)
   └── experiments (risultati reali)
```

---

## Componenti — Dettaglio e Motivazioni

### 1. Data Layer — PostgreSQL + SQLAlchemy

**Perché PostgreSQL e non SQLite:** il sistema cresce nel tempo con simulazioni e (potenzialmente) contributi esterni. PostgreSQL gestisce meglio concorrenza, query complesse su dati numerici, e future estensioni (es. pgvector per similarity search sui blend).

Tabelle principali:
- `ingredients` — proprietà fisico-chimiche di ogni farina GF
- `additives` — xantano, psyllium, guar gum, HPMC con proprietà funzionali
- `applications` — profili target per ogni uso (pizza, lievitati, frolla, pasta fresca)
- `blends` — formulazioni testate o simulate
- `simulation_results` — output del Physics Engine
- `experiment_results` — misure fisiche e score reali

### 2. Physics Engine — NumPy + SciPy

Tre moduli in pipeline:

**BlendCalculator**
Calcola le proprietà del blend a partire dalle proporzioni. Alcune proprietà sono additive per peso (proteine, amido totale, grassi). Altre non lo sono: la viscosità dipende da interazioni non lineari, specialmente con idrocolloidi come psyllium. Il modulo gestisce entrambi i casi con equazioni empiriche dalla letteratura.

**FermentationSimulator**
ODE system basato su cinetica di Michaelis-Menten per la produzione di CO₂ dal lievito, con dipendenza dalla temperatura tramite equazione di Arrhenius. La CO₂ trattenuta dipende dalla viscosità dell'impasto (output di BlendCalculator). Produce la curva di lievitazione: volume in funzione del tempo.

```
dCO2/dt = Vmax × [S] / (Km + [S]) × exp(-Ea/RT) × [X]
V(t) = V0 × (1 + η × CO2_trapped(t))
```

**BakingSimulator**
PDE di trasferimento di calore 1D risolta con differenze finite. Include:
- Termine di evaporazione dell'acqua (latent heat)
- Cinetica di gelatinizzazione dell'amido (equazione di Avrami, parametri dalla temp. di gelatinizzazione del blend)
- Cinetica di Maillard alla superficie (colore crosta)

**Perché questo approccio fisico invece di un semplice modello ML:** il physics engine funziona senza dati. Può essere costruito subito, usato per esplorare lo spazio, e serve come prior informato per il modello ML. Un ML puro su dati scarsi allucinherebbe; la fisica vincola le previsioni in regioni ragionevoli anche fuori distribuzione.

### 3. ML Layer — GPyTorch

**Gaussian Process Regression con kernel physics-informed.**

Perché GPR e non un neural network standard:
- Funziona bene con pochi dati (problema centrale di questo dominio)
- Fornisce uncertainty estimates — fondamentale per sapere dove il modello è sicuro e dove no
- Il kernel può encodare similarità fisica tra blend, non solo similarità nelle proporzioni raw

Il kernel opera nello spazio delle features fisiche (output del BlendCalculator) invece che nello spazio delle frazioni grezze. Due blend con proporzioni diverse ma proprietà fisiche simili sono trattati come simili — che è corretto dal punto di vista del dominio.

Con dati sufficienti (>200 esperimenti) si può passare a un **Bayesian Neural Network** o **Deep Ensemble** mantenendo l'uncertainty quantification.

### 4. Multi-Fidelity Bayesian Optimization — BoTorch

Il componente più sofisticato. BoTorch (Meta, PyTorch-based) ha il multi-fidelity BO built-in.

**Come funziona:**
1. Il BO ha due "osservazioni" per ogni blend: simulazione (fidelity 0, gratis) ed esperimento reale (fidelity 1, costoso)
2. Impara la correlazione tra le due fidelity — quanto la simulazione predice l'esperimento reale
3. Sceglie il prossimo blend da valutare e a quale fidelity, bilanciando costo e informazione

**Acquisition function: qNEHVI** (quasi-Monte Carlo Noisy Expected Hypervolume Improvement)
Gestisce ottimizzazione multi-obiettivo (es. massimizzare volume E morbidezza E minimizzare costo) con rumore nelle misure. È SOTA per questo tipo di problema.

**Perché questo risolve il problema dei dati:** invece di fare esperimenti random o seguire intuizione, il sistema dice esplicitamente "questo blend, se testato, mi darebbe la massima informazione rispetto a ciò che non so ancora". Ogni esperimento fisico ha il massimo impatto sul modello.

### 5. API Layer — FastAPI

Endpoints principali:
- `POST /blend/simulate` — esegue il physics engine su un blend
- `POST /blend/score` — score ML con uncertainty
- `POST /blend/optimize` — trova il blend ottimale per una applicazione
- `GET /blend/suggest-experiment` — suggerisce il prossimo esperimento da fare
- `POST /experiment/submit` — inserisce i risultati di un esperimento reale

FastAPI per: performance async, validazione automatica con Pydantic, auto-documentazione OpenAPI.

### 6. UI Layer

**MVP: Streamlit**
Permette di costruire l'interfaccia in ore. Utile per validare il flusso UX e testare il sistema senza investire in frontend.

**Produzione: React + Plotly**
Le visualizzazioni (curve di lievitazione, profili di temperatura, comparazione blend, Pareto frontier multi-obiettivo) richiedono interattività che Streamlit non gestisce bene oltre il prototipo.

---

## Stack Tecnologico — Riepilogo

| Layer | Tecnologia | Motivazione |
|---|---|---|
| Physics sim | NumPy + SciPy | ODE/PDE standard, zero dipendenze pesanti |
| ML / GP | GPyTorch | GP flessibile su PyTorch, kernel custom |
| BO | BoTorch | Multi-fidelity SOTA, stesso ecosistema PyTorch |
| Data | PostgreSQL + SQLAlchemy | Robusto, estendibile, query numeriche |
| API | FastAPI | Async, Pydantic, auto-docs |
| UI MVP | Streamlit | Velocità di sviluppo |
| UI prod | React + Plotly | Interattività avanzata |
| Container | Docker + Compose | Riproducibilità ambiente |

---

## Sequenza di Build

### Fase 1 — Data Model e Ingredient DB
- Schema DB completo con SQLAlchemy
- Modelli Pydantic per validazione input/output
- Popolamento ingredient DB con 10-15 farine GF comuni (dati da letteratura scientifica)
- Definizione profili applicazione: pizza, lievitati dolci, frolla, pasta fresca, pane

*Perché prima:* tutto il sistema dipende da dati ben strutturati. Un data model sbagliato si paga per tutta la vita del progetto.

### Fase 2 — Physics Engine
- BlendCalculator con proprietà additive e non
- FermentationSimulator (ODE)
- BakingSim (PDE 1D + cinetica amido + Maillard)
- Test unitari con valori noti dalla letteratura (es. curva di lievitazione standard)

*Perché seconda:* genera dati sintetici gratuitamente, serve come prior per ML, validabile indipendentemente.

### Fase 3 — ML Layer
- GPR baseline addestrato su output del physics engine
- Kernel physics-informed
- Uncertainty quantification e calibrazione

*Perché terza:* costruita sul physics engine, può essere sviluppata e testata anche senza dati sperimentali reali.

### Fase 4 — BO + Multi-Fidelity
- Integrazione BoTorch
- Multi-fidelity setup (sim = fidelity 0, esperimento = fidelity 1)
- qNEHVI per multi-obiettivo
- Loop completo: simula → predici → suggerisci → aggiorna

*Perché quarta:* richiede ML funzionante, è il componente che chiude il loop e rende il sistema utile.

### Fase 5 — API
- FastAPI endpoints
- Validazione input, gestione errori
- Documentazione OpenAPI

### Fase 6 — UI
- Streamlit MVP per validazione rapida
- Visualizzazioni: curve simulazione, radar plot proprietà blend, comparazione formule, Pareto frontier

---

## Applicazioni Target (v1)

| Applicazione | Proprietà critiche | Difficoltà modellazione |
|---|---|---|
| Pizza | Estensibilità, croccantezza bordo, tenuta topping | Media — ben studiata in letteratura |
| Lievitati dolci | Volume, alveolatura, morbidezza, shelf life | Alta — molte variabili di processo |
| Frolla | Sbriciolabilità, tenuta forma, assenza gommosità | Bassa — meno dipendente da lievitazione |
| Pasta fresca | Coesione, tenuta in cottura, texture al dente | Media — processo diverso (no cottura in forno) |
| Pane | Crosta, crumb structure, volume | Alta — simile a lievitati dolci ma più complesso |

---

## Farine GF Candidate (v1)

| Farina | Ruolo principale | Note |
|---|---|---|
| Riso (fine) | Base neutra | La più usata, basso assorbimento |
| Riso (integrale) | Base con più fibra | Sapore più marcato |
| Tapioca (amido) | Legante, elasticità | Alta amilopectina → gommosità se in eccesso |
| Mais (amido) | Croccantezza, leggerezza | Gelatinizza a temp. più alta |
| Patata (amido) | Morbidezza, umidità | Shelf life migliore |
| Grano saraceno | Proteine, struttura, sapore | Sapore caratteristico, non per tutto |
| Sorgo | Proteine, struttura | Profilo più simile al frumento tra i GF |
| Mandorla | Grassi, densità, umidità | Costosa, cambia molto texture |
| Teff | Micronutrienti, fibra | Sapore forte, nichia |
| Psyllium | Binding, ritenzione gas | Additivo critico — non è una farina |
| Xantano | Elasticità, struttura | Additivo critico — dosaggio preciso |

---

## Metriche di Qualità

### Fisiche (oggettive, misurabili)
- **Volume specifico** (cm³/g) — struttura, lievitazione
- **Durezza** (N) — texture, misurabile con texturometro o proxy manuale
- **Umidità residua** (%) — shelf life, sensazione in bocca
- **Colore crosta** (L*a*b*) — reazione di Maillard, appetibilità

### Sensoriali (strutturate)
Rubrica a 5 dimensioni, scala 1-5, per ridurre soggettività:
- Struttura / tenuta
- Texture in bocca
- Sapore / retrogusto
- Lavorabilità dell'impasto (pre-cottura)
- Aspetto visivo

### Nel modello
Le metriche fisiche diventano sia features intermedie che target. Le sensoriali sono il target finale. Il modello impara la relazione tra proprietà fisiche (predette dalla simulazione) e qualità finale.

---

## Note di Sviluppo

- Il physics engine deve essere **modulare**: ogni simulatore (fermentazione, cottura) deve poter essere usato indipendentemente e testato isolatamente
- I parametri del physics engine devono essere **esplicitamente separati** dai parametri ML: i primi vengono dalla letteratura e non si aggiornano con i dati, i secondi si aggiornano
- Ogni esperimento reale deve registrare **tutte le variabili di processo** (temperatura ambiente, umidità, tempo di lievitazione effettivo) non solo la formulazione — sono confounders importanti
- Partire con un'applicazione sola (pizza consigliata — la più studiata in letteratura GF) e espandere dopo aver validato il pipeline completo

---

## Piano Esecutivo

### Decisioni di Progetto

| Decisione | Scelta | Motivazione |
|---|---|---|
| Python | 3.13 | Ultima release, performance migliorate |
| Package manager | `uv` | Velocità, lockfile moderno, gestione Python |
| Database (dev) | SQLite | Zero setup, basta SQLAlchemy, migrabile a PostgreSQL in prod |
| Struttura repo | Monorepo con namespace | `glutenix/` come pacchetto principale, sottopacchetti separati |
| Dati iniziali | Ricerca in letteratura | Da popolare manualmente nella Fase 1 |
| Esperimenti reali | No (fase attuale) | Solo simulativo fino a Fase 4+ |

### Struttura del Repository

```
glutenix/
├── pyproject.toml          # uv project config
├── README.md
├── LICENSE
├── .gitignore
├── glutenix/
│   ├── __init__.py
│   ├── config.py           # Configurazione globale
│   ├── db/                 # SQLAlchemy models + engine
│   │   ├── __init__.py
│   │   ├── base.py         # Engine, Session, Base
│   │   ├── models.py       # Dichiarative models
│   │   └── seed.py         # Popolamento iniziale
│   ├── schemas/            # Pydantic models
│   │   ├── __init__.py
│   │   └── models.py
│   ├── ingredients/        # Dati da letteratura + lookup
│   │   ├── __init__.py
│   │   └── data.py
│   ├── engine/             # Physics Engine (Fase 2)
│   │   ├── __init__.py
│   │   ├── blend.py
│   │   ├── fermentation.py
│   │   └── baking.py
│   ├── ml/                 # ML Layer (Fase 3)
│   │   └── __init__.py
│   ├── bo/                 # Bayesian Optimization (Fase 4)
│   │   └── __init__.py
│   └── api/                # FastAPI (Fase 5)
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_engine.py
│   └── ...
└── data/                   # Dati grezzi (CSV/JSON)
    └── ingredients/
```

### Fase 1 — Data Model e Ingredient DB

| Step | Cosa | Deliverable |
|---|---|---|
| 1.1 | `uv init`, struttura progetto, `.gitignore` | Progetto Python con `pyproject.toml` |
| 1.2 | Modelli SQLAlchemy | `db/models.py` con tabelle: `Ingredient`, `Blend`, `Application`, `SimulationResult`, `ExperimentResult` |
| 1.3 | Modelli Pydantic | `schemas/models.py` per validazione I/O |
| 1.4 | Repository GitHub | `git init`, commit, push su repo pubblico |
| 1.5 | Popolamento ingredienti | Ricerca letteratura → `seed.py` con ~15 farine GF + ~4 addensanti + 5 applicazioni |
| 1.6 | Test | `test_models.py` — creazione DB, seed, query |

### Fase 2 — Physics Engine

| Step | Cosa |
|---|---|
| 2.1 | `BlendCalculator` — proprietà additive e non-lineari del blend |
| 2.2 | `FermentationSimulator` — ODE cinetica Michaelis-Menten + Arrhenius |
| 2.3 | `BakingSimulator` — PDE calore 1D + Avrami gelatinizzazione + Maillard |
| 2.4 | Test unitari con valori di riferimento da letteratura |

### Fase 3 — ML Layer

| Step | Cosa |
|---|---|
| 3.1 | GPR con GPyTorch su output Physics Engine |
| 3.2 | Kernel physics-informed |
| 3.3 | Uncertainty quantification |

### Fase 4 — BO + Multi-Fidelity

| Step | Cosa |
|---|---|
| 4.1 | Integrazione BoTorch |
| 4.2 | Multi-fidelity (sim=fidelity 0, exp=fidelity 1) |
| 4.3 | qNEHVI acquisition function |

### Fase 5 — API

| Step | Cosa |
|---|---|
| 5.1 | FastAPI endpoints (`/blend/simulate`, `/blend/optimize`, `/blend/score`, `/blend/suggest-experiment`) |
| 5.2 | Validazione Pydantic, error handling, OpenAPI docs |

### Fase 6 — UI

| Step | Cosa |
|---|---|
| 6.1 | Streamlit MVP: simulazione blend, curve lievitazione, radar plot proprietà |
| 6.2 | (Futuro) React + Plotly per produzione |
