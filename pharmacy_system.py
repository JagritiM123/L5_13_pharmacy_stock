
"""Pharmacy prescription and stock tracking application."""

import json
import sqlite3
from datetime import date, datetime, timedelta

conn = sqlite3.connect(":memory:")
stock = {}
prescriptions = []


def setup_database():
    """Create and populate the sample patient database."""
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                allergy TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            """
            INSERT OR IGNORE INTO patients (id, name, allergy)
            VALUES (?, ?, ?)
            """,
            [
                ("P1", "Kavya", "penicillin"),
                ("P2", "Arjun", "none"),
                ("P3", "Meena", "ibuprofen"),
            ],
        )


def find_patient(name):
    """Find a patient's ID and allergy using their name."""
    with conn:
        return conn.execute(
            "SELECT id, allergy FROM patients WHERE name = ?",
            (name,),
        ).fetchall()


def add_stock(drug, units, expiry, batch_log=None):
    """Add a positive quantity of medicine to stock."""
    if not isinstance(units, int) or isinstance(units, bool) or units <= 0:
        raise ValueError("Stock quantity must be a positive integer.")

    try:
        date.fromisoformat(expiry)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Expiry must use YYYY-MM-DD format."
        ) from error

    if batch_log is None:
        batch_log = []

    existing_drug = next(
        (name for name in stock if name.casefold() == drug.casefold()),
        None,
    )

    if existing_drug is not None:
        stock[existing_drug]["units"] += units
        stock[existing_drug]["expiry"] = expiry
    else:
        stock[drug] = {"units": units, "expiry": expiry}

    batch_log.append((drug, units))
    return len(batch_log)


def dispense(patient_name, drug, units):
    """Dispense medicine after validating the patient, allergy, and stock."""
    if not isinstance(units, int) or isinstance(units, bool) or units <= 0:
        return False

    patients = find_patient(patient_name)
    if not patients:
        return False

    patient_id, allergy = patients[0]

    stock_key = next(
        (name for name in stock if name.casefold() == drug.casefold()),
        None,
    )
    if stock_key is None:
        return False

    allergy_name = allergy.strip().casefold()
    if (
        allergy_name not in ("", "none")
        and allergy_name == drug.strip().casefold()
    ):
        print("Allergy warning for", patient_name)
        return False

    medicine = stock[stock_key]
    if medicine["units"] < units:
        return False

    if date.fromisoformat(medicine["expiry"]) < date.today():
        print("Medicine has expired:", stock_key)
        return False

    medicine["units"] -= units
    prescriptions.append(
        {
            "patient": patient_id,
            "drug": stock_key,
            "units": units,
            "time": datetime.now().isoformat(timespec="seconds"),
        }
    )
    return True


def expiring_soon(days=30):
    """Return non-expired medicines expiring within the given number of days."""
    if not isinstance(days, int) or isinstance(days, bool) or days < 0:
        raise ValueError("Days must be a non-negative integer.")

    today = date.today()
    last_day = today + timedelta(days=days)
    soon = []

    for drug, details in stock.items():
        expiry_date = date.fromisoformat(details["expiry"])
        if today <= expiry_date <= last_day:
            soon.append(drug)

    return soon


def expired_medicines():
    """Return medicines whose expiry dates are in the past."""
    today = date.today()
    return [
        drug
        for drug, details in stock.items()
        if date.fromisoformat(details["expiry"]) < today
    ]


def export_prescriptions(file="prescriptions.json"):
    """Export prescription records to a JSON file."""
    with open(file, "w", encoding="utf-8") as output_file:
        json.dump(prescriptions, output_file, indent=2)


def load_stock(file="stock.json"):
    """Load stock data from JSON, returning empty stock if unavailable."""
    try:
        with open(file, "r", encoding="utf-8") as stock_file:
            data = json.load(stock_file)
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as error:
        print(f"Could not load stock file: {error}")
        return {}

    if not isinstance(data, dict):
        print(
        "Could not load stock file: expected a JSON object."
        )
        return {}

    for drug, details in data.items():
        if (
            not isinstance(drug, str)
            or not isinstance(details, dict)
            or not isinstance(details.get("units"), int)
            or isinstance(details.get("units"), bool)
            or details["units"] < 0
            or not isinstance(details.get("expiry"), str)
        ):
            print("Could not load stock file: invalid medicine record.")
            return {}

        try:
            date.fromisoformat(details["expiry"])
        except ValueError:
            print("Could not load stock file: invalid expiry date.")
            return {}

    return data


def print_stock():
    """Display current stock quantities and expiry dates."""
    print("Pharmacy Stock")
    for drug, details in stock.items():
        print(
            f"{drug} -> {details['units']} units, "
            f"expires {details['expiry']}"
        )


def main():
    """Run the pharmacy stock and prescription tracker."""
    setup_database()
    stock.update(load_stock())

    add_stock("Paracetamol", 100, "2027-03-01")
    add_stock("Amoxicillin", 20, "2025-12-31")
    add_stock("Penicillin", 50, "2027-01-15")
    add_stock("Ibuprofen", 15, "2026-11-30")

    print("Arjun gets Amoxicillin:",dispense("Arjun", "Amoxicillin", 30),)
    print("Kavya gets Penicillin:", dispense("Kavya", "Penicillin", 10))
    print("Meena gets ibuprofen:", dispense("Meena", "ibuprofen", 2))
    print("Unknown patient:", dispense("Ghost", "Paracetamol", 5))

    name = input("Patient name to look up (Enter for Arjun): ") or "Arjun"
    print("Lookup result:", find_patient(name))
    print("Expiring within 30 days:", expiring_soon())
    print("Already expired:", expired_medicines())

    export_prescriptions()
    print_stock()


if __name__ == "__main__":
    main()
