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


# Repository B - Tester: Check real CSV failures through the command-line program.
class TesterCsvTests(unittest.TestCase):
    def test_truncated_rows_name_missing_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.csv"
            for row, columns in (("Ember,Fire,1,2", ("Speed",)),
                                 ("Ember,Fire,1", ("Defense", "Speed")),
                                 ("Ember", ("Type 1", "Attack", "Defense", "Speed"))):
                with self.subTest(row=row):
                    path.write_text("Name,Type 1,Attack,Defense,Speed\n" + row,
                                    encoding="utf-8")
                    with self.assertRaises(ValueError) as caught:
                        main.load_pokemon(path)
                    self.assertIn("row 2", str(caught.exception))
                    for column in columns:
                        self.assertIn(column, str(caught.exception))

    def test_actual_dataset_errors_exit_one_without_prompt_or_traceback(self):
        header = b"Name,Type 1,Attack,Defense,Speed\n"
        cases = {
            "missing": (None, "Could not load"),
            "empty": (b"", "No Pokémon"),
            "header only": (header, "No Pokémon"),
            "missing column": (b"Name,Type 1,Attack,Defense\n", "Speed"),
            "encoding": (b"\xff", "Could not load"),
            "malformed": (header + b'"unclosed,Fire,1,2,3', "Could not load"),
            "short row": (header + b"Ember,Fire,1,2", "Speed"),
            "negative": (header + b"Ember,Fire,-1,2,3", "row 2: Attack"),
            "missing name": (header + b",Fire,1,2,3", "row 2: missing Name"),
            "extra field": (header + b"Ember,Fire,1,2,3,4", "row 2"),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "main.py"
            script.write_bytes(Path(main.__file__).read_bytes())
            (root / "data").mkdir()
            dataset = root / "data/pokemon.csv"
            for label, (content, message) in cases.items():
                with self.subTest(case=label):
                    if content is not None:
                        dataset.write_bytes(content)
                    result = subprocess.run([sys.executable, str(script)],
                                            input="fire\n", capture_output=True,
                                            text=True, timeout=10)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn(message, result.stdout)
                    self.assertNotIn("Enter a primary", result.stdout)
                    self.assertEqual(result.stderr, "")
                    if dataset.exists():
                        dataset.unlink()


# Repository B - Tester: Independently calculate expected output from the shipped CSV.
class TesterRealDataTests(unittest.TestCase):
    def test_all_primary_types_against_independent_expected_output(self):
        root = Path(main.__file__).resolve().parent
        with (root / "data/pokemon.csv").open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        types = sorted({row["Type 1"].strip().lower() for row in rows})
        with tempfile.TemporaryDirectory() as directory:
            for primary in types:
                with self.subTest(primary=primary):
                    matches = [row for row in rows
                               if row["Type 1"].strip().lower() == primary]
                    expected = sorted(matches, key=lambda row: (
                        -sum(int(row[c]) for c in ("Attack", "Defense", "Speed")),
                        row["Name"].strip().lower()))[:5]
                    result = subprocess.run([sys.executable, str(root / "main.py")],
                                            cwd=directory, input="  " + primary.upper() + "  \n",
                                            capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    actual = result.stdout.split("Recommendations: ", 1)[1].splitlines()
                    lines = [str(len(expected))]
                    for index, row in enumerate(expected, 1):
                        score = sum(int(row[c]) for c in ("Attack", "Defense", "Speed"))
                        lines.append(f"{index}. {row['Name'].strip()} ({row['Type 1'].strip()}) | "
                                     f"Attack: {int(row['Attack'])} | Defense: {int(row['Defense'])} | "
                                     f"Speed: {int(row['Speed'])} | Score: {score}")
                    self.assertEqual(actual, lines)

    def test_real_closed_input_and_invalid_then_valid(self):
        script = str(Path(main.__file__).resolve())
        for user_input, retries, ending in (("", 0, "Goodbye!"),
                                            ("\n  \npizza\n WaTeR \n", 3, "Recommendations: 5"),
                                            ("pizza\n", 1, "Goodbye!")):
            with self.subTest(user_input=user_input):
                result = subprocess.run([sys.executable, script], input=user_input,
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, "")
                self.assertEqual(result.stdout.count("Please enter an available"), retries)
                self.assertIn(ending, result.stdout)


# Repository B - Tester: Verify real-dataset ranking and tie behavior.
class TesterWaterRankingTests(unittest.TestCase):
    def test_real_water_ranking_and_ties(self):
        # These expectations deliberately pin the bundled dataset. Intentional
        # data changes may require reviewing and updating this regression test.
        csv_path = Path(main.__file__).resolve().parent / "data/pokemon.csv"
        pokemon = main.load_pokemon(csv_path)
        recommendations = main.recommend_pokemon(pokemon, " WaTeR ")

        self.assertEqual(len(recommendations), 5)
        names = [entry["Name"] for entry in recommendations]
        self.assertEqual(names, [
            "Cloyster",
            "GyaradosMega Gyarados",
            "KyogrePrimal Kyogre",
            "SwampertMega Swampert",
            "Kingler",
        ])
        self.assertEqual([main.calculate_score(entry)
                          for entry in recommendations[:2]], [345, 345])
        self.assertLess(names[0].lower(), names[1].lower())
        self.assertTrue(all(entry["Type 1"] == "Water"
                            for entry in recommendations))


if __name__ == "__main__":
    unittest.main()
