"""Seed database with initial gluten-free ingredients and applications.

Data sourced from USDA FoodData Central and peer-reviewed literature.
Values are approximate (averages across varieties/references).
"""

import structlog

from glutenix.db.base import SessionLocal
from glutenix.db.models import Application, Ingredient

logger = structlog.get_logger("glutenix.db.seed")


def seed_database(session=None):
    if session is None:
        session = SessionLocal()
        close_session = True
    else:
        close_session = False

    try:
        _seed_ingredients(session)
        _seed_applications(session)
        session.commit()
        logger.info("db_seeded")
    except Exception:
        session.rollback()
        raise
    finally:
        if close_session:
            session.close()


def _seed_ingredients(session):
    existing_names = {name for (name,) in session.query(Ingredient.name).all()}
    if existing_names:
        logger.warning("ingredients_partially_seeded", existing_count=len(existing_names))

    ingredients = [
        Ingredient(
            name="White rice flour",
            category="flour",
            scientific_name="Oryza sativa",
            description="Finely milled white rice, neutral base flour",
            protein_pct=5.9, starch_pct=80.1, fat_pct=1.4,
            fiber_pct=2.4, moisture_pct=11.5, ash_pct=0.6,
            water_absorption=1.2,
            gelatinization_temp_min=68, gelatinization_temp_max=78,
            amylose_pct=19.0,
            kcal_per_100g=366.0, sugars_pct=0.1, saturated_fat_pct=0.4, sodium_mg_per_100g=0.0,
        ),
        Ingredient(
            name="Brown rice flour",
            category="flour",
            scientific_name="Oryza sativa (whole grain)",
            description="Whole grain rice flour with bran, more fiber",
            protein_pct=7.2, starch_pct=75.6, fat_pct=2.8,
            fiber_pct=4.5, moisture_pct=11.0, ash_pct=1.5,
            water_absorption=1.4,
            gelatinization_temp_min=68, gelatinization_temp_max=78,
            amylose_pct=19.0,
            kcal_per_100g=363.0, sugars_pct=0.7, saturated_fat_pct=0.6, sodium_mg_per_100g=8.0,
        ),
        Ingredient(
            name="Buckwheat flour",
            category="flour",
            scientific_name="Fagopyrum esculentum",
            description="Pseudocereal with strong flavor, high protein",
            protein_pct=11.1, starch_pct=67.0, fat_pct=3.0,
            fiber_pct=4.0, moisture_pct=13.0, ash_pct=2.1,
            water_absorption=1.6,
            gelatinization_temp_min=62, gelatinization_temp_max=72,
            amylose_pct=25.0,
            kcal_per_100g=335.0, sugars_pct=2.6, saturated_fat_pct=0.6, sodium_mg_per_100g=11.0,
        ),
        Ingredient(
            name="Sorghum flour",
            category="flour",
            scientific_name="Sorghum bicolor",
            description="Mild flavor, closest functional profile to wheat among GF",
            protein_pct=8.4, starch_pct=73.0, fat_pct=3.1,
            fiber_pct=3.7, moisture_pct=11.0, ash_pct=1.5,
            water_absorption=1.3,
            gelatinization_temp_min=69, gelatinization_temp_max=80,
            amylose_pct=23.0,
            kcal_per_100g=359.0, sugars_pct=1.9, saturated_fat_pct=0.5, sodium_mg_per_100g=3.0,
        ),
        Ingredient(
            name="Teff flour",
            category="flour",
            scientific_name="Eragrostis tef",
            description="Ancient grain, high in minerals and fiber",
            protein_pct=9.6, starch_pct=71.0, fat_pct=2.4,
            fiber_pct=5.5, moisture_pct=11.0, ash_pct=2.5,
            water_absorption=1.5,
            gelatinization_temp_min=68, gelatinization_temp_max=82,
            amylose_pct=18.0,
            kcal_per_100g=367.0, sugars_pct=1.5, saturated_fat_pct=0.4, sodium_mg_per_100g=12.0,
        ),
        Ingredient(
            name="Almond flour",
            category="flour",
            scientific_name="Prunus dulcis",
            description="Blanched almond meal, high fat, moist crumb",
            protein_pct=21.2, starch_pct=20.0, fat_pct=49.5,
            fiber_pct=12.5, moisture_pct=5.0, ash_pct=2.8,
            water_absorption=1.0,
            kcal_per_100g=579.0, sugars_pct=4.4, saturated_fat_pct=3.8, sodium_mg_per_100g=1.0,
        ),
        Ingredient(
            name="Millet flour",
            category="flour",
            scientific_name="Panicum miliaceum",
            description="Small grain flour, mild sweet flavor",
            protein_pct=10.8, starch_pct=69.0, fat_pct=3.4,
            fiber_pct=4.0, moisture_pct=11.5, ash_pct=1.8,
            water_absorption=1.5,
            gelatinization_temp_min=67, gelatinization_temp_max=78,
            amylose_pct=21.0,
            kcal_per_100g=365.0, sugars_pct=0.2, saturated_fat_pct=0.6, sodium_mg_per_100g=4.0,
        ),
        Ingredient(
            name="Oat flour (GF)",
            category="flour",
            scientific_name="Avena sativa",
            description="Certified gluten-free oat flour, nutty flavor",
            protein_pct=14.0, starch_pct=62.0, fat_pct=6.5,
            fiber_pct=8.0, moisture_pct=9.0, ash_pct=1.8,
            water_absorption=1.8,
            gelatinization_temp_min=58, gelatinization_temp_max=65,
            amylose_pct=27.0,
            kcal_per_100g=404.0, sugars_pct=0.8, saturated_fat_pct=1.2, sodium_mg_per_100g=8.0,
        ),
        Ingredient(
            name="Quinoa flour",
            category="flour",
            scientific_name="Chenopodium quinoa",
            description="Pseudocereal, complete protein, mild grassy note",
            protein_pct=14.1, starch_pct=58.0, fat_pct=6.1,
            fiber_pct=5.5, moisture_pct=11.0, ash_pct=2.4,
            water_absorption=1.7,
            gelatinization_temp_min=55, gelatinization_temp_max=70,
            amylose_pct=11.0,
            kcal_per_100g=357.0, sugars_pct=1.7, saturated_fat_pct=0.7, sodium_mg_per_100g=7.0,
        ),
        Ingredient(
            name="Tapioca starch",
            category="starch",
            scientific_name="Manihot esculenta",
            description="Cassava starch, high amylopectin, chewy texture",
            protein_pct=0.2, starch_pct=88.0, fat_pct=0.1,
            fiber_pct=0.5, moisture_pct=11.0, ash_pct=0.1,
            water_absorption=0.8,
            gelatinization_temp_min=58, gelatinization_temp_max=70,
            amylose_pct=17.0,
            kcal_per_100g=358.0, sugars_pct=0.0, saturated_fat_pct=0.0, sodium_mg_per_100g=1.0,
        ),
        Ingredient(
            name="Potato starch",
            category="starch",
            scientific_name="Solanum tuberosum",
            description="High swelling power, soft moist crumb",
            protein_pct=0.1, starch_pct=87.0, fat_pct=0.1,
            fiber_pct=0.1, moisture_pct=12.0, ash_pct=0.3,
            water_absorption=0.7,
            gelatinization_temp_min=56, gelatinization_temp_max=67,
            amylose_pct=21.0,
            kcal_per_100g=357.0, sugars_pct=0.0, saturated_fat_pct=0.0, sodium_mg_per_100g=18.0,
        ),
        Ingredient(
            name="Corn starch",
            category="starch",
            scientific_name="Zea mays",
            description="Maize starch, crispness and lightness",
            protein_pct=0.3, starch_pct=87.0, fat_pct=0.1,
            fiber_pct=0.1, moisture_pct=11.0, ash_pct=0.1,
            water_absorption=0.6,
            gelatinization_temp_min=62, gelatinization_temp_max=72,
            amylose_pct=27.0,
            kcal_per_100g=357.0, sugars_pct=0.0, saturated_fat_pct=0.0, sodium_mg_per_100g=9.0,
        ),
        Ingredient(
            name="Sweet rice flour (Mochiko)",
            category="flour",
            scientific_name="Oryza sativa (glutinous)",
            description="Glutinous (waxy) rice flour, very sticky, chewy",
            protein_pct=6.5, starch_pct=79.0, fat_pct=1.0,
            fiber_pct=1.5, moisture_pct=11.5, ash_pct=0.5,
            water_absorption=1.1,
            gelatinization_temp_min=63, gelatinization_temp_max=72,
            amylose_pct=1.0,
            kcal_per_100g=364.0, sugars_pct=0.1, saturated_fat_pct=0.4, sodium_mg_per_100g=0.0,
        ),
        Ingredient(
            name="Xanthan gum",
            category="hydrocolloid",
            scientific_name="Xanthomonas campestris",
            description="Polysaccharide binder, provides elasticity and structure",
            protein_pct=3.0, starch_pct=0.0, fat_pct=0.5,
            fiber_pct=75.0, moisture_pct=10.0, ash_pct=8.0,
            water_absorption=15.0,
            kcal_per_100g=240.0, sugars_pct=0.0, saturated_fat_pct=0.0, sodium_mg_per_100g=80.0,
        ),
        Ingredient(
            name="Psyllium husk",
            category="hydrocolloid",
            scientific_name="Plantago ovata",
            description="Soluble fiber, excellent water binding and gas retention",
            protein_pct=3.0, starch_pct=0.0, fat_pct=0.5,
            fiber_pct=85.0, moisture_pct=8.0, ash_pct=3.0,
            water_absorption=25.0,
            kcal_per_100g=200.0, sugars_pct=0.3, saturated_fat_pct=0.0, sodium_mg_per_100g=10.0,
        ),
        Ingredient(
            name="Guar gum",
            category="hydrocolloid",
            scientific_name="Cyamopsis tetragonoloba",
            description="Galactomannan, thickening and stabilising agent",
            protein_pct=5.0, starch_pct=0.0, fat_pct=0.5,
            fiber_pct=80.0, moisture_pct=10.0, ash_pct=1.0,
            water_absorption=20.0,
            kcal_per_100g=260.0, sugars_pct=0.0, saturated_fat_pct=0.0, sodium_mg_per_100g=2.0,
        ),
        Ingredient(
            name="HPMC (Hydroxypropyl Methylcellulose)",
            category="hydrocolloid",
            description="Cellulose derivative, film-forming, gas retention",
            protein_pct=0.0, starch_pct=0.0, fat_pct=0.0,
            fiber_pct=90.0, moisture_pct=5.0, ash_pct=3.0,
            water_absorption=12.0,
            kcal_per_100g=200.0, sugars_pct=0.0, saturated_fat_pct=0.0, sodium_mg_per_100g=50.0,
        ),
        Ingredient(
            name="Amaranth flour",
            category="flour",
            scientific_name="Amaranthus spp.",
            description="Pseudocereal flour used in gluten-free pasta and bakery applications",
            protein_pct=13.6, starch_pct=62.0, fat_pct=7.0,
            fiber_pct=6.7, moisture_pct=10.0, ash_pct=2.9,
            water_absorption=1.7,
            gelatinization_temp_min=62, gelatinization_temp_max=68,
            amylose_pct=8.0,
            kcal_per_100g=371.0, sugars_pct=1.7, saturated_fat_pct=1.5, sodium_mg_per_100g=4.0,
        ),
        Ingredient(
            name="Sodium alginate",
            category="hydrocolloid",
            scientific_name="Alginate sodium salt",
            description="Alginate hydrocolloid, calcium-gelling, useful for pasta structure and cooking-loss reduction",
            protein_pct=0.0, starch_pct=0.0, fat_pct=0.0,
            fiber_pct=80.0, moisture_pct=12.0, ash_pct=8.0,
            water_absorption=30.0,
            kcal_per_100g=200.0, sugars_pct=0.0, saturated_fat_pct=0.0, sodium_mg_per_100g=9000.0,
        ),
        Ingredient(
            name="High-amylose rice flour",
            category="flour",
            scientific_name="Oryza sativa high-amylose cultivar",
            description="Rice flour with elevated amylose content used for extruded gluten-free pasta",
            protein_pct=7.0, starch_pct=78.16, fat_pct=1.0,
            fiber_pct=1.5, moisture_pct=12.0, ash_pct=0.6,
            water_absorption=1.3,
            gelatinization_temp_min=70.55, gelatinization_temp_max=79.12,
            amylose_pct=28.12,
            kcal_per_100g=365.0, sugars_pct=0.1, saturated_fat_pct=0.2, sodium_mg_per_100g=2.0,
        ),
        Ingredient(
            name="Konjac glucomannan",
            category="hydrocolloid",
            scientific_name="Amorphophallus konjac glucomannan",
            description="Highly hydrophilic neutral polysaccharide used for viscosity, water retention, and starch-digestion reduction",
            protein_pct=0.0, starch_pct=0.0, fat_pct=0.0,
            fiber_pct=85.0, moisture_pct=8.0, ash_pct=2.0,
            water_absorption=35.0,
            kcal_per_100g=180.0, sugars_pct=0.0, saturated_fat_pct=0.0, sodium_mg_per_100g=80.0,
        ),
        Ingredient(
            name="Curdlan",
            category="hydrocolloid",
            scientific_name="Beta-1,3-glucan curdlan",
            description="Thermo-irreversible heat-setting beta-glucan gel former used in rice pasta structure",
            protein_pct=0.0, starch_pct=0.0, fat_pct=0.0,
            fiber_pct=90.0, moisture_pct=8.0, ash_pct=1.0,
            water_absorption=25.0,
            kcal_per_100g=180.0, sugars_pct=0.0, saturated_fat_pct=0.0, sodium_mg_per_100g=50.0,
        ),
        Ingredient(
            name="Soy protein isolate",
            category="flour",
            scientific_name="Glycine max protein isolate",
            description="High-protein soy isolate used to reinforce starch-protein networks in gluten-free pasta",
            protein_pct=88.0, starch_pct=1.0, fat_pct=1.0,
            fiber_pct=2.0, moisture_pct=6.0, ash_pct=4.0,
            water_absorption=2.5,
            gelatinization_temp_min=None, gelatinization_temp_max=None,
            amylose_pct=None,
            kcal_per_100g=335.0, sugars_pct=0.5, saturated_fat_pct=0.2, sodium_mg_per_100g=1000.0,
        ),
        Ingredient(
            name="Chickpea flour",
            category="flour",
            scientific_name="Cicer arietinum",
            description="Legume flour with high protein and fiber used in gluten-free bread enrichment",
            protein_pct=22.0, starch_pct=48.0, fat_pct=6.2,
            fiber_pct=13.0, moisture_pct=7.3, ash_pct=3.0,
            water_absorption=1.9,
            gelatinization_temp_min=64.0, gelatinization_temp_max=78.0,
            amylose_pct=28.0,
            kcal_per_100g=387.0, sugars_pct=2.7, saturated_fat_pct=0.7, sodium_mg_per_100g=30.0,
        ),
        Ingredient(
            name="Whey protein concentrate",
            category="flour",
            scientific_name="Bos taurus whey protein concentrate",
            description="Dairy protein concentrate used as a gluten-free bread structuring protein",
            protein_pct=73.0, starch_pct=0.0, fat_pct=6.1,
            fiber_pct=0.0, moisture_pct=5.0, ash_pct=0.7,
            water_absorption=1.5,
            gelatinization_temp_min=None, gelatinization_temp_max=None,
            amylose_pct=None,
            kcal_per_100g=390.0, sugars_pct=9.1, saturated_fat_pct=3.8, sodium_mg_per_100g=300.0,
        ),
        Ingredient(
            name="Commercial gluten-free bread mix",
            category="flour",
            scientific_name="Composite gluten-free bread mix",
            description="Approximate aggregate for literature records where a commercial bread mix composition is only partially disclosed",
            protein_pct=6.5, starch_pct=78.0, fat_pct=1.2,
            fiber_pct=5.0, moisture_pct=11.0, ash_pct=1.8,
            water_absorption=1.7,
            gelatinization_temp_min=64.0, gelatinization_temp_max=78.0,
            amylose_pct=22.0,
            kcal_per_100g=355.0, sugars_pct=1.0, saturated_fat_pct=0.3, sodium_mg_per_100g=600.0,
        ),
        Ingredient(
            name="Corn flour",
            category="flour",
            scientific_name="Zea mays flour",
            description="Finely milled corn flour used in gluten-free bread formulations",
            protein_pct=6.9, starch_pct=76.0, fat_pct=3.9,
            fiber_pct=7.3, moisture_pct=10.9, ash_pct=1.0,
            water_absorption=1.2,
            gelatinization_temp_min=62.0, gelatinization_temp_max=74.0,
            amylose_pct=25.0,
            kcal_per_100g=361.0, sugars_pct=0.6, saturated_fat_pct=0.5, sodium_mg_per_100g=5.0,
        ),
        Ingredient(
            name="Modified starch (ADA)",
            category="starch",
            scientific_name="Acetylated distarch adipate",
            description="Cross-linked modified starch used for process tolerance and crumb structure",
            protein_pct=0.2, starch_pct=86.0, fat_pct=0.1,
            fiber_pct=0.1, moisture_pct=12.0, ash_pct=0.3,
            water_absorption=1.0,
            gelatinization_temp_min=64.0, gelatinization_temp_max=76.0,
            amylose_pct=24.0,
            kcal_per_100g=355.0, sugars_pct=0.0, saturated_fat_pct=0.0, sodium_mg_per_100g=20.0,
        ),
        Ingredient(
            name="Sodium caseinate",
            category="flour",
            scientific_name="Bos taurus sodium caseinate",
            description="Milk protein ingredient used for structure and nutrition in gluten-free bread",
            protein_pct=90.0, starch_pct=0.0, fat_pct=1.5,
            fiber_pct=0.0, moisture_pct=5.0, ash_pct=4.0,
            water_absorption=2.0,
            gelatinization_temp_min=None, gelatinization_temp_max=None,
            amylose_pct=None,
            kcal_per_100g=365.0, sugars_pct=0.2, saturated_fat_pct=0.9, sodium_mg_per_100g=1200.0,
        ),
        Ingredient(
            name="Flaxseed flour",
            category="flour",
            scientific_name="Linum usitatissimum",
            description="Ground flaxseed, high in fiber and omega-3, used in low-carb GF bread",
            protein_pct=40.0, starch_pct=3.9, fat_pct=8.8,
            fiber_pct=34.0, moisture_pct=5.0, ash_pct=6.9,
            water_absorption=3.0,
            gelatinization_temp_min=None, gelatinization_temp_max=None,
            amylose_pct=None,
            kcal_per_100g=450.0, sugars_pct=1.6, saturated_fat_pct=0.8, sodium_mg_per_100g=30.0,
        ),
        Ingredient(
            name="Pea protein powder",
            category="flour",
            scientific_name="Pisum sativum protein concentrate",
            description="Yellow pea protein isolate used for protein enrichment in GF bread",
            protein_pct=78.4, starch_pct=7.2, fat_pct=6.8,
            fiber_pct=4.0, moisture_pct=5.0, ash_pct=4.5,
            water_absorption=2.5,
            gelatinization_temp_min=None, gelatinization_temp_max=None,
            amylose_pct=None,
            kcal_per_100g=380.0, sugars_pct=0.5, saturated_fat_pct=1.0, sodium_mg_per_100g=800.0,
        ),
        Ingredient(
            name="Potato fiber",
            category="hydrocolloid",
            scientific_name="Solanum tuberosum fiber",
            description="Dietary fiber concentrate from potato, used for water binding and texture in GF bread",
            protein_pct=1.0, starch_pct=2.0, fat_pct=0.2,
            fiber_pct=85.0, moisture_pct=6.0, ash_pct=2.0,
            water_absorption=8.0,
            gelatinization_temp_min=None, gelatinization_temp_max=None,
            amylose_pct=None,
            kcal_per_100g=180.0, sugars_pct=0.1, saturated_fat_pct=0.0, sodium_mg_per_100g=20.0,
        ),
    ]
    missing = [ingredient for ingredient in ingredients if ingredient.name not in existing_names]
    if missing:
        session.add_all(missing)
        logger.info("ingredients_added", count=len(missing))


def _seed_applications(session):
    if session.query(Application).count() > 0:
        logger.warning("applications_already_seeded")
        return

    applications = [
        Application(
            name="Pizza",
            description="Neapolitan-style GF pizza: extensible dough, crispy edge, topping hold",
            target_properties='{"volume": "medium", "elasticity": "high", "crispness": "high", "moisture": "low-medium"}',
        ),
        Application(
            name="Pane",
            description="Sandwich bread: high volume, soft crumb, good shelf life",
            target_properties='{"volume": "high", "elasticity": "medium", "softness": "high", "shelf_life_days": 3}',
        ),
        Application(
            name="Lievitati dolci",
            description="Brioche, donuts, sweet leavened pastries",
            target_properties='{"volume": "high", "softness": "high", "sweetness": "medium", "shelf_life_days": 2}',
        ),
        Application(
            name="Frolla",
            description="Shortcrust pastry for cookies and tart shells",
            target_properties='{"crumbliness": "high", "shape_hold": "high", "crispness": "high", "moisture": "low"}',
        ),
        Application(
            name="Pasta fresca",
            description="Fresh egg pasta: cohesive sheet, cooking tolerance",
            target_properties='{"cohesion": "high", "cooking_tolerance": "high", "elasticity": "medium", "moisture": "medium"}',
        ),
    ]
    session.add_all(applications)
