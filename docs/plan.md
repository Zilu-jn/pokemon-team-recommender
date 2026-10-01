# Pokémon Team Recommender — Project Plan

## 1. Problem the Project Solves

A Pokémon dataset can contain many entries, making it difficult to choose Pokémon of a preferred type. This command-line program will recommend up to five Pokémon whose **primary type** matches the user's preference.

Each Pokémon receives a simple score:

**Score = Attack + Defense + Speed**

Higher scores rank first. The project provides a simple ranking, rather than a complete team strategy.

## 2. User Input and Program Output

### Input

The user enters one preferred primary type, such as `Fire`, `Water`, or `grass`.

The dataset is stored at `data/pokemon.csv` and must contain these columns:

| Column | Purpose |
|---|---|
| `Name` | Pokémon name |
| `Type 1` | Primary type |
| `Attack` | Attack statistic |
| `Defense` | Defense statistic |
| `Speed` | Speed statistic |

Extra columns are ignored. Statistics must be non-negative whole numbers. Use a UTF-8 CSV file.

### Output

Display the number of matches being recommended and a numbered list containing:

- Pokémon name and primary type
- Attack, Defense, and Speed
- Total score

Return at most five entries, sorted by score from highest to lowest. Break score ties by Pokémon name alphabetically, ignoring capitalization. If both score and name match, preserve CSV order.

When fewer than five Pokémon match, display all available matches. Each CSV row represents one entry; alternate forms remain separate entries.

Only primary type is considered. A matching secondary type alone does not qualify.

## 3. File and Folder Structure

```text
pokemon-team-recommender/
├── main.py                  # Application functions and user interaction
├── Dockerfile               # Instructions for building the Docker image
├── .dockerignore            # Files excluded from the Docker build context
├── data/
│   └── pokemon.csv          # Pokémon dataset
├── docs/
│   └── plan.md              # Project plan
├── tests/
│   └── test_main.py         # Tests using small sample datasets
└── README.md                # Dataset source and local/Docker instructions
```

Use only Python's standard library, including `csv`, `pathlib`, `unittest`, and `tempfile`. No third-party Python packages or `requirements.txt` are needed.

## 4. Main Python Functions

Keep the application functions in `main.py`.

| Function | Responsibility |
|---|---|
| `load_pokemon(csv_path)` | Read the CSV into a list of dictionaries, check required columns, trim names and types, validate data, and convert statistics to integers. |
| `normalize_type(user_input)` | Remove surrounding whitespace and convert the type to lowercase for comparison. |
| `get_available_types(pokemon)` | Return sorted, unique primary types, treating capitalization differences as the same type. |
| `calculate_score(pokemon)` | Return Attack + Defense + Speed for one entry. |
| `recommend_pokemon(pokemon, preferred_type, limit=5)` | Filter by normalized primary type, sort using the defined tie rules, and return up to `limit` entries. |
| `display_recommendations(recommendations)` | Print the result count and numbered recommendations with statistics and scores. |
| `main()` | Locate and load the dataset, show available types, request valid input, and display recommendations. Handle errors with friendly messages. |

Keep input and printing separate from the ranking logic so the logic can be tested easily. Importing `main.py` for tests must not start an interactive prompt.

### Program Flow

1. Locate `data/pokemon.csv` relative to `main.py` using `pathlib`.
2. Load and validate the dataset.
3. Display available primary types.
4. Ask for a preferred type.
5. Normalize and validate the response.
6. Ask again if the response is invalid.
7. Rank and display up to five matching Pokémon.
8. Exit after one recommendation list.

## 5. Input and Data Error Handling

### User Input

- Treat `Fire`, `FIRE`, and `fire` identically.
- Accept surrounding whitespace, such as ` Water `.
- Reject blank or whitespace-only input.
- Validate against primary types present in the dataset.
- For an unknown or unavailable type, show a helpful message and available types, then ask again.
- Do not attempt spelling correction.
- If input closes or the user presses Ctrl+C, exit with a short message and no traceback.

### Dataset Errors

Use strict validation to keep the behavior understandable:

| Problem | Behavior |
|---|---|
| Missing or unreadable file | Explain the problem and stop |
| Missing required column | Name the missing column and stop |
| Missing name or primary type | Identify the CSV row and stop |
| Missing, nonnumeric, fractional, or negative statistic | Identify the row and column and stop |
| Empty or header-only dataset | Explain that no Pokémon are available and stop |
| Invalid encoding or unreadable CSV structure | Explain that the dataset could not be read and stop |

Do not silently skip invalid records. Dataset errors should end the program with a nonzero exit status; successful recommendations should exit with status zero.

## 6. Beginner-Friendly Containerization Plan

Docker will package Python, the application, and the dataset into one image. A container is a running instance of that image.

### Planned Dockerfile

The Dockerfile will:

1. Start from an official Python slim image with an explicit version, such as `python:3.12-slim`.
2. Set the container working directory to `/app`.
3. Copy `main.py`, `data/`, and `tests/` into `/app`, preserving their structure.
4. Set the default command to run `python main.py` using Docker's exec-form `CMD`.

The application should start when the container runs, not while the image builds. `WORKDIR` establishes the directory used by subsequent Dockerfile instructions. See the [Dockerfile overview](https://docs.docker.com/build/concepts/dockerfile/).

### Planned .dockerignore

Exclude unnecessary local files:

- `.git/`
- `.venv/` and `venv/`
- `__pycache__/` and compiled Python files
- Editor settings such as `.vscode/` and `.idea/`
- Operating-system files such as `.DS_Store`
- `docs/`

Keep `main.py`, `data/pokemon.csv`, and `tests/` available to the build. Docker reads `.dockerignore` from the build context to exclude files before sending them to the builder. See [Docker build context documentation](https://docs.docker.com/build/concepts/context/).

### Build the Image

Install Docker and ensure its engine is running. Open a terminal in the project root, where the Dockerfile is located.

```bash
docker build -t pokemon-team-recommender .
```

The final `.` selects the current folder as the build context. See [Docker image build](https://docs.docker.com/reference/cli/docker/image/build/).

### Run Interactively

```bash
docker run --rm -it pokemon-team-recommender
```

Enter a type when prompted.

- `-i` keeps standard input open.
- `-t` provides a terminal for interaction.
- `--rm` removes the container after it exits.

These options support a simple terminal-based interaction. See [Docker container run](https://docs.docker.com/reference/cli/docker/container/run/).

No ports, volumes, Docker Compose, or external services are needed. The CSV is included in the image, so rebuild after changing the application or dataset.

## 7. Testing Plan

Use small, invented datasets with scores that are easy to calculate. Use temporary CSV files for loader tests instead of modifying the real dataset.

### Automated Tests

| Case | Expected Result |
|---|---|
| Valid type with more than five matches | Exactly the five highest-ranked entries |
| Valid type with exactly five matches | All five entries |
| Valid type with one to four matches | All matches without adding duplicates |
| Different input capitalization | Identical recommendations |
| Input with surrounding whitespace | Same result as trimmed input |
| Blank or unknown type | Rejected by input validation |
| Attack 60, Defense 50, Speed 70 | Score equals 180 |
| Tied scores | Names sorted alphabetically, ignoring capitalization |
| Identical score and name | Original CSV order preserved |
| Secondary-type-only match | Entry excluded |
| Recommendation function receives an unmatched type | Empty list returned |
| Missing file or required column | Clear error for `main()` to handle |
| Invalid statistic or missing name/type | Error identifies the row or field |
| Empty or header-only CSV | Clear error without a crash |

Run locally:

```bash
python -m unittest discover -s tests
```

### Manual Application Checks

1. Run `python main.py` with the real dataset.
2. Enter a valid primary type and check scores, ordering, and result count.
3. Enter an invalid type followed by a valid type; confirm the program asks again and succeeds.
4. Test mixed capitalization and surrounding whitespace.
5. Press Ctrl+C at the prompt and confirm a clean exit.
6. Confirm that output and error messages are readable.

### Docker Verification

Perform these checks after implementation:

1. **Build the image** using the build command above. Confirm the command finishes successfully.
2. **Run tests inside the image:**

   ```bash
   docker run --rm pokemon-team-recommender python -m unittest discover -s tests
   ```

   Confirm tests are discovered and all pass.

3. **Start the interactive container:**

   ```bash
   docker run --rm -it pokemon-team-recommender
   ```

   Confirm available types and the input prompt appear.

4. **Enter a valid type.** Confirm recommendations match the local program when both use the same dataset.
5. **Run again with invalid input, then valid input.** Confirm validation and retry behavior work inside Docker.
6. **Check completion.** Confirm the program exits after displaying recommendations and returns control to the terminal.
7. **Check missing input handling:**

   ```bash
   docker run --rm pokemon-team-recommender
   ```

   With no interactive input attached, confirm the program exits with a helpful message instead of a traceback or endless retry loop.

A successful image build alone is insufficient; the interactive run verifies that the dataset path and input handling work.

## 8. Risks and Design Concerns

| Concern | Simple Design Decision |
|---|---|
| Invalid CSV data could produce incorrect scores or crashes | Validate the entire dataset before prompting; report the problem and stop |
| Interactive input may be unavailable in Docker | Document `docker run --rm -it`; handle closed input gracefully |
| Tied scores could make ranking unclear | Use alphabetical names as the tie-breaker and preserve CSV order for exact ties |
| Host and Docker file paths differ | Locate the CSV relative to `main.py`; preserve `data/pokemon.csv` inside `/app` |
| Image contains an older dataset or code version | Rebuild the image after changes |

## 9. Acceptance Criteria

The completed project must meet these requirements:

- [ ] Runs locally using `python main.py`.
- [ ] Uses only Python's standard library.
- [ ] Loads and validates `data/pokemon.csv`.
- [ ] Resolves the dataset path relative to `main.py`.
- [ ] Shows available primary types before requesting input.
- [ ] Ignores capitalization and surrounding whitespace when matching types.
- [ ] Rejects blank, unknown, or unavailable types and asks again.
- [ ] Handles closed input and Ctrl+C without an unexplained traceback.
- [ ] Recommends Pokémon matching the requested primary type only.
- [ ] Calculates every score as Attack + Defense + Speed.
- [ ] Applies descending score order and the documented tie-breakers.
- [ ] Returns five entries when at least five matches exist, or all matches when fewer exist.
- [ ] Displays names, primary types, statistics, scores, and the recommendation count.
- [ ] Reports invalid or unavailable datasets clearly and exits with a nonzero status.
- [ ] Passes automated tests locally and inside Docker.
- [ ] Includes a Dockerfile and `.dockerignore`.
- [ ] Builds successfully with the documented Docker build command.
- [ ] Runs interactively with the documented Docker run command.
- [ ] Produces equivalent local and Docker results for the same dataset and input.
- [ ] README documents the dataset source, required columns, local commands, Docker commands, and when to rebuild.

## 10. Scope Limits

The first version includes one CSV, one preferred primary type, and one ranked recommendation list.

Exclude graphical interfaces, web APIs, secondary-type filtering, type-matchup strategy, machine learning, saving teams, Docker Compose, and external services.
