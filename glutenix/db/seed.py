"""Seed database with initial gluten-free ingredients and applications.

Data sourced from USDA FoodData Central and peer-reviewed literature.
Values are approximate (averages across varieties/references).
"""

from glutenix.db.base import SessionLocal
from glutenix.db.models import Application, Ingredient


def seed_database():
    session = SessionLocal()
    try:
        _seed_ingredients(session)
        _seed_applications(session)
        session.commit()
        print("Database seeded successfully.")
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def _seed_ingredients(session):
    if session.query(Ingredient).count() > 0:
        return

    ingredients = [
        # --- Flours ---
        Ingredient(
            name="White rice flour",
            category="flour",
            description="Finely milled white rice, neutral base flour",
            protein_pct=5.9,
            starch_pct=80.1,
            fat_pct=1.4,
            fiber_pct=2.4,
            moisture_pct=11.5,
            ash_pct=0.6,
            water_absorption=1.2,
            gelatinization_temp_min=68,
            gelatinization_temp_max=78,
            amylose_pct=19.0,
        ),
        Ingredient(
            name="Brown rice flour",
            category="flour",
            description="Whole grain rice flour with bran, more fiber",
            protein_pct=7.2,
            starch_pct=75.6,
            fat_pct=2.8,
            fiber_pct=4.5,
            moisture_pct=11.0,
            ash_pct=1.5,
            water_absorption=1.4,
            gelatinization_temp_min=68,
            gelatinization_temp_max=78,
            amylose_pct=19.0,
        ),
        Ingredient(
            name="Buckwheat flour",
            category="flour",
            description="Pseudocereal with strong flavor, high protein",
            protein_pct=11.1,
            starch_pct=67.0,
            fat_pct=3.0,
            fiber_pct=4.0,
            moisture_pct=13.0,
            ash_pct=2.1,
            water_absorption=1.6,
            gelatinization_temp_min=62,
            gelatinization_temp_max=72,
            amylose_pct=25.0,
        ),
        Ingredient(
            name="Sorghum flour",
            category="flour",
            description="Mild flavor, closest functional profile to wheat among GF",
            protein_pct=8.4,
            starch_pct=73.0,
            fat_pct=3.1,
            fiber_pct=3.7,
            moisture_pct=11.0,
            ash_pct=1.5,
            water_absorption=1.3,
            gelatinization_temp_min=69,
            gelatinization_temp_max=80,
            amylose_pct=23.0,
        ),
        Ingredient(
            name="Teff flour",
            category="flour",
            description="Ancient grain, high in minerals and fiber",
            protein_pct=9.6,
            starch_pct=71.0,
            fat_pct=2.4,
            fiber_pct=5.5,
            moisture_pct=11.0,
            ash_pct=2.5,
            water_absorption=1.5,
            gelatinization_temp_min=68,
            gelatinization_temp_max=82,
            amylose_pct=18.0,
        ),
        Ingredient(
            name="Almond flour",
            category="flour",
            description="Blanched almond meal, high fat, moist crumb",
            protein_pct=21.2,
            starch_pct=20.0,
            fat_pct=49.5,
            fiber_pct=12.5,
            moisture_pct=5.0,
            ash_pct=2.8,
            water_absorption=1.0,
            gelatinization_temp_min=None,
            gelatinization_temp_max=None,
            amylose_pct=None,
        ),
        Ingredient(
            name="Millet flour",
            category="flour",
            description="Small grain flour, mild sweet flavor",
            protein_pct=10.8,
            starch_pct=69.0,
            fat_pct=3.4,
            fiber_pct=4.0,
            moisture_pct=11.5,
            ash_pct=1.8,
            water_absorption=1.5,
            gelatinization_temp_min=67,
            gelatinization_temp_max=78,
            amylose_pct=21.0,
        ),
        Ingredient(
            name="Oat flour (GF)",
            category="flour",
            description="Certified gluten-free oat flour, nutty flavor",
            protein_pct=14.0,
            starch_pct=62.0,
            fat_pct=6.5,
            fiber_pct=8.0,
            moisture_pct=9.0,
            ash_pct=1.8,
            water_absorption=1.8,
            gelatinization_temp_min=58,
            gelatinization_temp_max=65,
            amylose_pct=27.0,
        ),
        Ingredient(
            name="Quinoa flour",
            category="flour",
            description="Pseudocereal, complete protein, mild grassy note",
            protein_pct=14.1,
            starch_pct=58.0,
            fat_pct=6.1,
            fiber_pct=5.5,
            moisture_pct=11.0,
            ash_pct=2.4,
            water_absorption=1.7,
            gelatinization_temp_min=55,
            gelatinization_temp_max=70,
            amylose_pct=11.0,
        ),
        # --- Starches ---
        Ingredient(
            name="Tapioca starch",
            category="starch",
            description="Cassava starch, high amylopectin, chewy texture",
            protein_pct=0.2,
            starch_pct=88.0,
            fat_pct=0.1,
            fiber_pct=0.5,
            moisture_pct=11.0,
            ash_pct=0.1,
            water_absorption=0.8,
            gelatinization_temp_min=58,
            gelatinization_temp_max=70,
            amylose_pct=17.0,
        ),
        Ingredient(
            name="Potato starch",
            category="starch",
            description="High swelling power, soft moist crumb",
            protein_pct=0.1,
            starch_pct=87.0,
            fat_pct=0.1,
            fiber_pct=0.1,
            moisture_pct=12.0,
            ash_pct=0.3,
            water_absorption=0.7,
            gelatinization_temp_min=56,
            gelatinization_temp_max=67,
            amylose_pct=21.0,
        ),
        Ingredient(
            name="Corn starch",
            category="starch",
            description="Maize starch, crispness and lightness",
            protein_pct=0.3,
            starch_pct=87.0,
            fat_pct=0.1,
            fiber_pct=0.1,
            moisture_pct=11.0,
            ash_pct=0.1,
            water_absorption=0.6,
            gelatinization_temp_min=62,
            gelatinization_temp_max=72,
            amylose_pct=27.0,
        ),
        Ingredient(
            name="Sweet rice flour (Mochiko)",
            category="flour",
            description="Glutinous (waxy) rice flour, very sticky, chewy",
            protein_pct=6.5,
            starch_pct=79.0,
            fat_pct=1.0,
            fiber_pct=1.5,
            moisture_pct=11.5,
            ash_pct=0.5,
            water_absorption=1.1,
            gelatinization_temp_min=63,
            gelatinization_temp_max=72,
            amylose_pct=1.0,
        ),
        # --- Hydrocolloids ---
        Ingredient(
            name="Xanthan gum",
            category="hydrocolloid",
            description="Polysaccharide binder, provides elasticity and structure",
            protein_pct=3.0,
            starch_pct=0.0,
            fat_pct=0.5,
            fiber_pct=75.0,
            moisture_pct=10.0,
            ash_pct=8.0,
            water_absorption=15.0,
            gelatinization_temp_min=None,
            gelatinization_temp_max=None,
            amylose_pct=None,
        ),
        Ingredient(
            name="Psyllium husk",
            category="hydrocolloid",
            description="Soluble fiber, excellent water binding and gas retention",
            protein_pct=3.0,
            starch_pct=0.0,
            fat_pct=0.5,
            fiber_pct=85.0,
            moisture_pct=8.0,
            ash_pct=3.0,
            water_absorption=25.0,
            gelatinization_temp_min=None,
            gelatinization_temp_max=None,
            amylose_pct=None,
        ),
        Ingredient(
            name="Guar gum",
            category="hydrocolloid",
            description="Galactomannan, thickening and stabilising agent",
            protein_pct=5.0,
            starch_pct=0.0,
            fat_pct=0.5,
            fiber_pct=80.0,
            moisture_pct=10.0,
            ash_pct=1.0,
            water_absorption=20.0,
            gelatinization_temp_min=None,
            gelatinization_temp_max=None,
            amylose_pct=None,
        ),
        Ingredient(
            name="HPMC (Hydroxypropyl Methylcellulose)",
            category="hydrocolloid",
            description="Cellulose derivative, film-forming, gas retention",
            protein_pct=0.0,
            starch_pct=0.0,
            fat_pct=0.0,
            fiber_pct=90.0,
            moisture_pct=5.0,
            ash_pct=3.0,
            water_absorption=12.0,
            gelatinization_temp_min=None,
            gelatinization_temp_max=None,
            amylose_pct=None,
        ),
    ]
    session.add_all(ingredients)


def _seed_applications(session):
    if session.query(Application).count() > 0:
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
            target_properties='{"volume": "high", "crumb_softness": "high", "elasticity": "medium", "shelf_life_days": 3}',
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
