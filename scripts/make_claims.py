"""Generate a synthetic 100,000-row insurance claims Excel file: data/claims.xlsx."""

import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.stores import CLAIMS_XLSX

ROWS = 100_000
START, END = date(2022, 1, 1), date(2025, 12, 31)

CANTONS = {
    "Luxembourg": 30, "Esch-sur-Alzette": 30, "Capellen": 8, "Mersch": 5, "Diekirch": 5, "Grevenmacher": 5,
    "Remich": 4, "Echternach": 3, "Redange": 3, "Clervaux": 3, "Wiltz": 3, "Vianden": 1,
}
CHANNELS = {"Agent": 55, "Online": 30, "Broker": 15}
PRODUCTS = {"Home": 45, "Motor": 42, "Liability": 13}

# Each peril: weight, median claimed amount, and description fragments.
# The last fragment list holds (text, probability the claim is rejected).
PERILS = {
    "Home": {
        "Water damage": (35, 2200, [
            ["Burst pipe in the kitchen", "Leak from the upstairs neighbour's bathroom", "Washing machine hose came loose",
             "Overflowing bathtub", "Rain coming through the roof", "Frozen pipe split in the garage", "Dishwasher leaked overnight"],
            ["soaked the parquet floor.", "stained the ceiling below.", "damaged the kitchen cabinets.",
             "ruined the living room carpet.", "caused mould on the bedroom wall.", "damaged electrical sockets."],
            [("Plumber invoice attached.", 0.03), ("Photos sent the same day.", 0.03), ("", 0.04),
             ("Leak had been going on for several months.", 0.65), ("Tenant reported it to the landlord first.", 0.05)],
        ]),
        "Fire": (8, 9000, [
            ["Kitchen fire from a pan left on the stove", "Short circuit in an extension lead", "Candle tipped over on a shelf",
             "Fire spread from a barbecue on the terrace", "Faulty tumble dryer caught fire", "Chimney fire"],
            ["blackened the kitchen walls.", "destroyed the sofa and curtains.", "caused smoke damage throughout the flat.",
             "burned part of the roof structure.", "damaged the terrace furniture."],
            [("Fire brigade report attached.", 0.02), ("No one was injured.", 0.03), ("", 0.04),
             ("No smoke detector was installed.", 0.15)],
        ]),
        "Theft": (15, 1800, [
            ["Burglars forced the front door.", "Bicycle stolen from the building's common cellar.",
             "Jewellery taken while the family was on holiday.", "Laptop stolen through an open window.",
             "Garden tools stolen from the shed.", "Break-in through the balcony door."],
            ["Police report filed.", "Neighbours heard noise at night.", "Items included a TV and a games console.",
             "Items included a road bike worth over 2,000 EUR."],
            [("Receipts provided for all items.", 0.03), ("", 0.04), ("No sign of forced entry.", 0.7),
             ("The cellar door was left unlocked.", 0.6)],
        ]),
        "Storm": (30, 1500, [
            ["Strong winds tore off roof tiles", "A tree fell onto the garden fence", "Hail damaged the skylight",
             "Storm blew over the garden shed", "Heavy gusts broke the satellite dish"],
            ["and rain got into the attic.", "and the gutter was ripped off.", "and the conservatory roof cracked.",
             "and the neighbour's car was scratched."],
            [("Weather station recorded gusts above 100 km/h.", 0.02), ("Temporary repairs done by a roofer.", 0.03),
             ("", 0.04), ("Roof had not been maintained for years.", 0.4)],
        ]),
        "Glass breakage": (12, 600, [
            ["Window pane cracked", "Glass shower screen shattered", "Glass table top broke",
             "Patio door glass cracked", "Induction hob glass cracked"],
            ["after a ball hit it.", "for no apparent reason.", "when a heavy pot was dropped on it.",
             "during a sudden temperature change."],
            [("Glazier quote attached.", 0.03), ("", 0.04), ("Crack existed before the policy started.", 0.7)],
        ]),
    },
    "Motor": {
        "Collision": (45, 2800, [
            ["Rear-ended at a red light", "Hit a parked car while reversing", "Collision at a roundabout",
             "Skidded on ice and hit a barrier", "Side impact at a junction", "Scraped a pillar in an underground car park"],
            ["in the city centre.", "in a residential street.", "in a supermarket car park.", "on a country road."],
            ["Front bumper and headlight damaged.", "Rear door dented.", "Airbags deployed.",
             "Damage limited to scratches.", "Other driver admitted fault."],
            [("European accident report completed.", 0.02), ("", 0.04), ("Driver was not listed on the policy.", 0.6),
             ("Driver was over the alcohol limit.", 0.9)],
        ]),
        "Theft": (8, 12000, [
            ["Car stolen from the street overnight.", "Car stolen from a public car park.", "Catalytic converter stolen.",
             "Wheels and tyres stolen.", "Keyless entry car stolen from the driveway."],
            ["Police report filed.", "Vehicle found damaged two weeks later.", "Vehicle not recovered."],
            [("Both keys handed to the insurer.", 0.03), ("", 0.04), ("Keys were left inside the car.", 0.75)],
        ]),
        "Glass breakage": (25, 450, [
            ["Stone chip cracked the windscreen", "Windscreen cracked by a falling branch", "Side window smashed",
             "Rear window shattered in the cold"],
            ["on the motorway.", "while parked.", "during a long trip."],
            [("Repaired by an approved glass partner.", 0.02), ("", 0.04)],
        ]),
        "Vandalism": (12, 900, [
            ["Car keyed along both sides", "Mirrors broken off overnight", "Tyres slashed", "Graffiti sprayed on the bonnet"],
            ["in a residential street.", "outside the train station.", "in a public car park."],
            [("Police report filed.", 0.03), ("", 0.04), ("No police report filed.", 0.5)],
        ]),
        "Natural event": (10, 2500, [
            ["Hailstorm dented the roof and bonnet", "Car flooded by a rising river", "Tree branch fell on the car during a storm"],
            ["while parked outside.", "in a flooded underground garage.", "during a weekend trip."],
            [("", 0.04), ("Car was parked in a flood zone despite official warnings.", 0.3)],
        ]),
    },
    "Liability": {
        "Third-party property": (70, 1200, [
            ["Child kicked a ball through the neighbour's window.", "Dog damaged a neighbour's garden.",
             "Water from our flat leaked into the flat below.", "Knocked over a vase in a shop.",
             "Bicycle scratched a parked car.", "Dropped a borrowed laptop."],
            ["Neighbour sent a repair quote.", "Shop owner sent an invoice.", "Owner asked for a replacement."],
            [("", 0.05), ("Photos of the damage attached.", 0.04), ("Witness statement attached.", 0.04),
             ("Third party's insurer contacted.", 0.05), ("Damage was caused intentionally.", 0.95),
             ("Item belonged to a family member living in the same household.", 0.8)],
        ]),
        "Third-party injury": (30, 4000, [
            ["Visitor slipped on the wet stairs", "Cyclist collided with a pedestrian", "Dog bit a passer-by",
             "Child injured another child at a playground", "Guest tripped over a garden hose"],
            ["and broke a wrist.", "and needed stitches.", "and was treated at the hospital.", "and suffered bruises."],
            [("Medical certificate attached.", 0.03), ("", 0.05), ("Witness statement attached.", 0.04),
             ("Injured person is the policyholder's spouse.", 0.85)],
        ]),
    },
}


def pick(weights: dict) -> str:
    return random.choices(list(weights), weights=list(weights.values()))[0]


def random_date(peril: str) -> date:
    day = START + timedelta(days=random.randrange((END - START).days + 1))
    if peril == "Storm" and random.random() < 0.7:  # storms cluster in winter
        day = day.replace(month=random.choice([1, 2, 3, 11, 12]), day=min(day.day, 28))
    return day


def make_claim(i: int) -> dict:
    product = pick(PRODUCTS)
    peril = pick({name: spec[0] for name, spec in PERILS[product].items()})
    _, median, fragments = PERILS[product][peril]
    *parts, endings = fragments
    ending, reject_probability = random.choice(endings)
    description = " ".join(p for p in [*(random.choice(part) for part in parts), ending] if p)

    claim_date = random_date(peril)
    claimed = round(median * math.exp(random.gauss(0, 0.8)), 2)
    if (END - claim_date).days < 60 and random.random() < 0.7 or random.random() < 0.03:
        status, paid, days = "Open", None, None
    elif random.random() < reject_probability:
        status, paid, days = "Rejected", 0.0, int(random.lognormvariate(3.0, 0.5))
    else:
        status, paid = "Paid", round(claimed * random.uniform(0.7, 1.0), 2)
        days = int(random.lognormvariate(3.0, 0.6) * (1.5 if claimed > 5000 else 1))

    return {
        "claim_id": f"CLM-{i:06d}",
        "policy_id": f"POL-{random.randrange(1, 60_000):05d}",
        "claim_date": claim_date,
        "product": product,
        "peril": peril,
        "canton": pick(CANTONS),
        "channel": pick(CHANNELS),
        "customer_age": int(min(85, max(18, random.triangular(18, 85, 42)))),
        "claimed_amount": claimed,
        "paid_amount": paid,
        "status": status,
        "settlement_days": days,
        "description": description,
    }


CANTON_MISSPELLINGS = {
    "Esch-sur-Alzette": ["Esch/Alzette", "Esch sur Alzette", "esch-sur-alzette"],
    "Luxembourg": ["Luxemburg", "LUXEMBOURG", "Lux-Ville"],
    "Grevenmacher": ["Grevenmaacher"],
    "Diekirch": ["diekirch "],
}


def make_messy(df: pd.DataFrame) -> pd.DataFrame:
    """Make the file look like a real export: inconsistent spellings, mixed formats, duplicates, missing values.
    Uses its own random generator, so the clean data underneath is always the same."""
    mess = random.Random(7)
    df = df.astype(object)
    rows = list(df.index)

    for i in mess.sample(rows, 4000):
        if df.at[i, "canton"] in CANTON_MISSPELLINGS:
            df.at[i, "canton"] = mess.choice(CANTON_MISSPELLINGS[df.at[i, "canton"]])
    for i in mess.sample(rows, 2000):
        product = df.at[i, "product"]
        df.at[i, "product"] = mess.choice([product.upper(), product.lower(), f" {product} "])
    for i in mess.sample(rows, 2000):
        status = df.at[i, "status"]
        df.at[i, "status"] = mess.choice([status.upper(), status.lower()])
    for i in mess.sample(rows, 3000):
        day = df.at[i, "claim_date"]
        df.at[i, "claim_date"] = mess.choice([day.strftime("%d/%m/%Y"), day.strftime("%d.%m.%Y"), day.isoformat()])
    for i in mess.sample(rows, 3000):
        amount = f"{df.at[i, 'claimed_amount']:,.2f}"  # 1,234.56
        european = amount.replace(",", " ").replace(".", ",").replace(" ", ".")  # 1.234,56
        df.at[i, "claimed_amount"] = mess.choice([f"{european} €", f"EUR {amount}"])

    duplicates = df.loc[mess.sample(rows, 300)]
    broken = df.loc[mess.sample(rows, 60)].copy()
    broken["claim_id"] = [f"CLM-{ROWS + n:06d}" for n in range(1, 61)]
    broken["claimed_amount"] = None
    return pd.concat([df, duplicates, broken], ignore_index=True)


if __name__ == "__main__":
    random.seed(42)
    df = pd.DataFrame([make_claim(i) for i in range(1, ROWS + 1)])
    messy = make_messy(df)
    CLAIMS_XLSX.parent.mkdir(exist_ok=True)
    messy.to_excel(CLAIMS_XLSX, index=False, sheet_name="claims")
    print(f"Wrote {len(messy):,} rows ({ROWS:,} real claims + duplicates and broken rows) to {CLAIMS_XLSX}")
