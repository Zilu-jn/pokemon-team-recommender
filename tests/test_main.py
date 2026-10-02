"""Small invented datasets exercise loading, ranking, and terminal behavior."""

import contextlib
import csv
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import main


def entry(name="Ember", primary="Fire", attack=60, defense=50, speed=70):
    return {"Name": name, "Type 1": primary, "Attack": attack,
            "Defense": defense, "Speed": speed}


# Repository B - Builder: Temporary CSV files never alter the real dataset.
class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "sample.csv"

    def write_rows(self, rows, columns=main.REQUIRED_COLUMNS):
        with self.path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    def test_valid_data_trimmed_converted_and_extra_columns_ignored(self):
        row = entry(" Ember ", " Fire ", " 60 ", "0", "70")
        row["Type 2"] = "Water"
        self.write_rows([row], (*main.REQUIRED_COLUMNS, "Type 2"))
        self.assertEqual(main.load_pokemon(self.path), [entry(defense=0)])

    def test_each_required_column(self):
        for missing in main.REQUIRED_COLUMNS:
            with self.subTest(column=missing):
                columns = [c for c in main.REQUIRED_COLUMNS if c != missing]
                self.write_rows([], columns)
                with self.assertRaisesRegex(ValueError, missing):
                    main.load_pokemon(self.path)

    def test_invalid_statistics(self):
        for column in main.STAT_COLUMNS:
            for value in ("", "abc", "1.5", "-1", "1_000", "NaN"):
                with self.subTest(column=column, value=value):
                    row = entry()
                    row[column] = value
                    self.write_rows([row])
                    with self.assertRaisesRegex(ValueError, f"row 2: {column}"):
                        main.load_pokemon(self.path)

    def test_missing_name_or_type(self):
        for column in ("Name", "Type 1"):
            with self.subTest(column=column):
                row = entry()
                row[column] = "  "
                self.write_rows([row])
                with self.assertRaisesRegex(ValueError, f"row 2: missing {column}"):
                    main.load_pokemon(self.path)

    def test_empty_and_header_only(self):
        for text in ("", ",".join(main.REQUIRED_COLUMNS) + "\n"):
            with self.subTest(text=text):
                self.path.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "No Pokémon"):
                    main.load_pokemon(self.path)

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            main.load_pokemon(self.path)

    def test_bad_encoding(self):
        self.path.write_bytes(b"\xff")
        with self.assertRaises(UnicodeError):
            main.load_pokemon(self.path)

    def test_malformed_csv_and_incorrect_field_counts(self):
        header = ",".join(main.REQUIRED_COLUMNS) + "\n"
        for row in ('"unclosed,Fire,1,2,3', 'Ember,Fire,1,2',
                    'Ember,Fire,1,2,3,extra'):
            with self.subTest(row=row):
                self.path.write_text(header + row, encoding="utf-8")
                with self.assertRaises((ValueError, csv.Error)):
                    main.load_pokemon(self.path)

    def test_duplicate_headers(self):
        self.path.write_text(
            ",".join(main.REQUIRED_COLUMNS) + ",Attack\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unique"):
            main.load_pokemon(self.path)

    def test_invalid_later_row_is_not_silently_skipped(self):
        self.write_rows([entry(), entry(attack=-1)])
        with self.assertRaisesRegex(ValueError, "row 3: Attack"):
            main.load_pokemon(self.path)


# Repository B - Builder: Ranking tests check outcomes with hand-calculated scores.
class RankingTests(unittest.TestCase):
    def test_score(self):
        self.assertEqual(main.calculate_score(entry()), 180)

    def test_normalization_and_available_types(self):
        self.assertEqual(main.normalize_type(" FIRE "), "fire")
        self.assertEqual(main.get_available_types([
            entry(primary=" Fire "), entry(primary="FIRE"),
            entry(primary="Water")]), ["fire", "water"])

    def test_counts_and_best_five(self):
        for count in range(1, 8):
            with self.subTest(count=count):
                rows = [entry(name=f"Mon{i}", attack=i) for i in range(count)]
                result = main.recommend_pokemon(rows, "fire")
                self.assertEqual([r["Attack"] for r in result],
                                 list(reversed(range(count)))[:5])
                self.assertEqual(rows[0]["Attack"], 0)

    def test_type_matching(self):
        rows = [entry(primary=" FIRE "), entry("Brook", "Water")]
        for preferred in ("fire", "FIRE", " Fire "):
            with self.subTest(preferred=preferred):
                self.assertEqual(main.recommend_pokemon(rows, preferred), rows[:1])

    def test_ties_alphabetical_and_stable(self):
        first = entry("alpha", attack=60, defense=50)
        second = entry("ALPHA", attack=50, defense=60)
        rows = [entry("Zulu"), first, second, entry("Beta")]
        result = main.recommend_pokemon(rows, "fire")
        self.assertEqual(result, [first, second, rows[3], rows[0]])

    def test_secondary_type_does_not_match(self):
        row = entry(primary="Water")
        row["Type 2"] = "Fire"
        self.assertEqual(main.recommend_pokemon([row], "fire"), [])

    def test_no_matches(self):
        for preferred in ("", "unknown", "water"):
            self.assertEqual(main.recommend_pokemon([entry()], preferred), [])
        self.assertEqual(main.recommend_pokemon([], "fire"), [])

    def test_limit_never_exceeds_five(self):
        rows = [entry(name=f"Mon{i}") for i in range(8)]
        for limit, expected in ((0, 0), (-1, 0), (2, 2), (20, 5)):
            with self.subTest(limit=limit):
                self.assertEqual(len(main.recommend_pokemon(rows, "fire", limit)),
                                 expected)


# Repository B - Builder: Check display output directly with invented records.
class DisplayTests(unittest.TestCase):
    def test_empty_recommendations_display_zero_count(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.display_recommendations([])
        self.assertEqual(output.getvalue().strip(), "Recommendations: 0")

    def test_multiple_recommendations_display_all_details(self):
        recommendations = [
            entry("Ember", "Fire", 60, 50, 70),
            entry("Brook", "Water", 40, 65, 30),
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.display_recommendations(recommendations)
        self.assertEqual(output.getvalue().strip().splitlines(), [
            "Recommendations: 2",
            "1. Ember (Fire) | Attack: 60 | Defense: 50 | Speed: 70 | Score: 180",
            "2. Brook (Water) | Attack: 40 | Defense: 65 | Speed: 30 | Score: 135",
        ])


# Repository B - Builder: Mock input to test interaction without a live prompt.
class InteractionTests(unittest.TestCase):
    def run_main(self, inputs):
        output = io.StringIO()
        with patch("main.load_pokemon", return_value=[entry()]) as loader:
            with patch("builtins.input", side_effect=inputs):
                with contextlib.redirect_stdout(output):
                    status = main.main()
        expected_path = Path(main.__file__).resolve().parent / "data/pokemon.csv"
        loader.assert_called_once_with(expected_path)
        return status, output.getvalue()

    def test_invalid_then_valid_input(self):
        status, output = self.run_main(["", "   ", "unknown", " FIRE "])
        self.assertEqual(status, 0)
        self.assertEqual(output.count("Please enter an available"), 3)
        for text in ("Available primary types: fire", "Recommendations: 1",
                     "1. Ember (Fire)", "Attack: 60", "Defense: 50",
                     "Speed: 70", "Score: 180"):
            self.assertIn(text, output)

    def test_closed_input_and_interrupt(self):
        for error in (EOFError, KeyboardInterrupt):
            with self.subTest(error=error):
                status, output = self.run_main([error()])
                self.assertEqual(status, 0)
                self.assertIn("Input closed or cancelled", output)

    def test_dataset_errors_exit_before_prompt(self):
        for error in (FileNotFoundError("missing"), PermissionError("unreadable"),
                      ValueError("bad row"), UnicodeError("encoding"),
                      csv.Error("malformed")):
            with self.subTest(error=error):
                with patch("main.load_pokemon", side_effect=error):
                    with patch("builtins.input") as prompt:
                        with contextlib.redirect_stdout(io.StringIO()) as output:
                            self.assertEqual(main.main(), 1)
                        prompt.assert_not_called()
                        self.assertIn("Could not load", output.getvalue())

    def test_import_does_not_prompt(self):
        root = Path(main.__file__).resolve().parent
        result = subprocess.run([sys.executable, "-c", "import main"],
                                cwd=root, input="", capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_real_program_from_another_directory(self):
        script = Path(main.__file__).resolve()
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(script)], cwd=directory,
                                    input="fire\n", capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Recommendations: 5", result.stdout)
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
