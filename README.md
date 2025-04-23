# githubX

Automates fetching daily activity from various sources (GitHub, Garmin, potentially others) and posting engaging updates to social media (X/Twitter, potentially others) using an LLM.

## Project Structure

```
githubX/
├── .github/workflows/daily_report.yml # GitHub Action workflow
├── .gitignore
├── main.py                 # Main orchestrator script
├── config.yaml             # Central configuration file <--- IMPORTANT!
├── requirements.txt
├── README.md
└── src/                    # Source code modules
    ├── __init__.py
    ├── config_loader.py    # Loads config.yaml
    ├── data_sources/       # Modules for fetching data
    │   ├── __init__.py
    │   ├── github_source.py  # Fetches GitHub activity
    │   └── garmin_source.py  # Fetches Garmin activity (EXPERIMENTAL)
    │   # ... (add other sources here)
    ├── llm/                # Module for LLM interaction
    │   ├── __init__.py
    │   └── generator.py      # Generates post content
    └── posting/            # Modules for posting to platforms
        ├── __init__.py
        └── twitter_poster.py # Posts to X (Twitter)
        # ... (add other posters here)
```

## Setup

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/githubX.git # Replace with your repo URL
    cd githubX
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure `config.yaml`:**

    - Open the `config.yaml` file.
    - **Review and customize:**
      - `persona`: Defines the general voice/style for the LLM when no source-specific prompt is found.
      - `llm.model`: Choose the Gemini model (e.g., `gemini-1.5-flash`).
      - `llm.source_prompts`: **IMPORTANT!** Define specific prompts for each data source (`github`, `garmin`). This allows tailoring the tweet content based on the activity type (e.g., coding vs. fitness). The script will use the prompt matching the source key if available.
      - `llm.default_prompt_template`: A fallback prompt used if a source-specific prompt isn't defined.
      - `data_sources`: Enable/disable sources (`enabled: true/false`).
        - For each source, ensure `_env_var` keys (e.g., `username_env_var`, `pat_env_var`, `password_env_var`) match the GitHub Secrets you will create.
        - Customize `activity_format` for how data from each source is presented to the LLM.
        - **Note on Garmin:** The Garmin source (`garmin_source.py`) uses an unofficial library (`garminconnect`) which may be unstable or break if Garmin changes their systems.
      - `posting`: Enable/disable posting targets. Set limits (`max_posts_per_run`, `sleep_between_posts`). Ensure `_env_var` keys match the secrets.
    - **Secret Names:** Pay close attention to the `_env_var` values (e.g., `username_env_var: GH_USERNAME`, `password_env_var: GARMIN_PASSWORD`). These tell the script which GitHub Secret to look for. You _must_ create secrets with these exact names.

5.  **Configure GitHub Secrets:**
    Go to your repository's `Settings` > `Secrets and variables` > `Actions`.
    Click `New repository secret` and add secrets corresponding to **all** the `_env_var` names defined in your `config.yaml` for **enabled** sources and targets. For the default configuration (GitHub + Garmin + Twitter), you need:

    - `GH_USERNAME`: Your GitHub username (Note: Cannot start with `GITHUB_`).
    - `USER_GITHUB_PAT`: Your GitHub Personal Access Token (fine-grained with `Contents: Read-only`, `Metadata: Read-only` recommended, or classic with `repo` and `read:user`).
    - `GARMIN_USERNAME`: Your Garmin Connect login email/username.
    - `GARMIN_PASSWORD`: Your Garmin Connect password.
    - `GEMINI_API_KEY`: Your Google AI Studio API Key.
    - `X_API_KEY`: Your X App's API Key.
    - `X_API_SECRET`: Your X App's API Key Secret.
    - `X_ACCESS_TOKEN`: Your X App's Access Token.
    - `X_ACCESS_TOKEN_SECRET`: Your X App's Access Token Secret.

## Usage

The script is designed to be run automatically via the GitHub Actions workflow defined in `.github/workflows/daily_report.yml`.

- **Scheduled Run:** The workflow runs daily (default: 7:00 AM UTC). Edit the `cron` expression in the workflow file to change the schedule.
- **Randomized Start:** The script includes a random delay (default: 0-240 minutes) at the start to make the posting time less predictable. This delay happens _after_ the scheduled `cron` time.
- **Manual Run:** Trigger the workflow manually from the Actions tab in your GitHub repository (select the `master` or `main` branch).
- **Configuration:** Modify `config.yaml` to change behavior (prompts, enabled sources/targets, limits, etc.) and commit the changes.
- **Rate Limits:** Be mindful of Twitter API rate limits. If posts consistently fail with `429 Too Many Requests`, try increasing `sleep_between_posts` or reducing `max_posts_per_run` in `config.yaml`, or run the workflow less frequently.

## Local Development (Optional)

1.  Ensure you have completed steps 1-3 of Setup.
2.  Create a `.env` file in the project root (this file is ignored by git).
3.  Add your secrets to the `.env` file in the format `KEY=VALUE` (use the **exact names** defined as `_env_var` in `config.yaml`, e.g., `GH_USERNAME`, `GARMIN_PASSWORD`).
    Example `.env`:
    ```
    GH_USERNAME=your_github_username
    USER_GITHUB_PAT=ghp_or_github_pat_...
    GEMINI_API_KEY=ai_...
    GARMIN_USERNAME=your_garmin_email
    GARMIN_PASSWORD=your_garmin_password
    X_API_KEY=...
    X_API_SECRET=...
    X_ACCESS_TOKEN=...
    X_ACCESS_TOKEN_SECRET=...
    ```
4.  Modify `config.yaml` for local testing if needed.
5.  Run the script from the project root (use `python3` if needed):
    ```bash
    python main.py # Or python3 main.py
    ```
    *(Note: The script uses `src.config_loader.get_secret` which reads from `os.environ`. You need a mechanism to load `.env` into environment variables *before* the script runs for local testing. Tools like `python-dotenv` can do this. You can install it (`pip install python-dotenv`) and add `from dotenv import load_dotenv; load_dotenv()` at the very top of `main.py` for simple local testing.)*
