"""Recommend up to five Pokémon by primary type using a local CSV."""

import csv
from pathlib import Path

REQUIRED_COLUMNS = ("Name", "Type 1", "Attack", "Defense", "Speed")
STAT_COLUMNS = ("Attack", "Defense", "Speed")


# Repository B - Builder: Validate the complete dataset before accepting input.
def load_pokemon(csv_path):
    """Return validated records; raise a descriptive error for invalid data."""
    pokemon = []
    with open(csv_path, encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file, strict=True)
        if reader.fieldnames is None:
            raise ValueError("No Pokémon are available: the CSV is empty.")
        missing = [column for column in REQUIRED_COLUMNS
                   if column not in reader.fieldnames]
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(missing))
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("CSV column names must be unique.")

        for row in reader:
            row_number = reader.line_num
            if None in row:
                raise ValueError(f"CSV row {row_number}: incorrect number of fields.")
            # Repository B - Tester: Name absent columns in truncated CSV rows.
            missing_fields = [column for column, value in row.items() if value is None]
            if missing_fields:
                raise ValueError(
                    f"CSV row {row_number}: missing fields: " + ", ".join(missing_fields)
                )
            record = {}
            for column in ("Name", "Type 1"):
                value = row[column].strip()
                if not value:
                    raise ValueError(f"CSV row {row_number}: missing {column}.")
                record[column] = value
            for column in STAT_COLUMNS:
                value = row[column].strip()
                if not value.isascii() or not value.isdecimal():
                    raise ValueError(
                        f"CSV row {row_number}: {column} must be a "
                        "non-negative whole number."
                    )
                try:
                    record[column] = int(value)
                except ValueError as error:
                    raise ValueError(
                        f"CSV row {row_number}: {column} is too large to read."
                    ) from error
            pokemon.append(record)

    if not pokemon:
        raise ValueError("No Pokémon are available: the CSV has no data rows.")
    return pokemon


# Repository B - Builder: Normalize both dataset types and user input consistently.
def normalize_type(user_input):
    """Ignore surrounding whitespace and capitalization."""
    return user_input.strip().lower()


def get_available_types(pokemon):
    """Return sorted, unique normalized primary types."""
    return sorted({normalize_type(entry["Type 1"]) for entry in pokemon})


def calculate_score(pokemon):
    """Use the assignment's simple three-statistic score."""
    return pokemon["Attack"] + pokemon["Defense"] + pokemon["Speed"]


# Repository B - Builder: Stable sorting preserves CSV order for exact ties.
def recommend_pokemon(pokemon, preferred_type, limit=5):
    """Rank primary-type matches without changing the original list."""
    preferred_type = normalize_type(preferred_type)
    matches = [entry for entry in pokemon
               if normalize_type(entry["Type 1"]) == preferred_type]
    ranked = sorted(matches, key=lambda entry: (
        -calculate_score(entry), entry["Name"].lower()
    ))
    return ranked[:max(0, min(limit, 5))]


# Repository B - Builder: Keep terminal output separate from ranking logic.
def display_recommendations(recommendations):
    """Print the count, statistics, and score for each recommendation."""
    print(f"\nRecommendations: {len(recommendations)}")
    for number, entry in enumerate(recommendations, start=1):
        print(
            f"{number}. {entry['Name']} ({entry['Type 1']}) | "
            f"Attack: {entry['Attack']} | Defense: {entry['Defense']} | "
            f"Speed: {entry['Speed']} | Score: {calculate_score(entry)}"
        )


def main():
    """Run one interactive recommendation session and return an exit status."""
    # Repository B - Builder: This path works locally and inside /app in Docker.
    csv_path = Path(__file__).resolve().parent / "data" / "pokemon.csv"
    try:
        pokemon = load_pokemon(csv_path)
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        print(f"Could not load Pokémon dataset at {csv_path}: {error}")
        return 1

    available_types = get_available_types(pokemon)
    print("Available primary types: " + ", ".join(available_types))
    while True:
        try:
            preferred_type = normalize_type(input("Enter a primary Pokémon type: "))
        except (EOFError, KeyboardInterrupt):
            print("\nInput closed or cancelled. Goodbye!")
            return 0
        if preferred_type in available_types:
            break
        print("Please enter an available primary type: " + ", ".join(available_types))

    display_recommendations(recommend_pokemon(pokemon, preferred_type))
    return 0


# Repository B - Builder: Importing this module never starts the input prompt.
if __name__ == "__main__":
    raise SystemExit(main())
