# githubX

Automates fetching daily activity from various sources (GitHub, potentially others) and posting engaging updates to social media (X/Twitter, potentially others) using an LLM.

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
    │   └── github_source.py  # Fetches GitHub activity
    │   # ... (add other sources like garmin_source.py here)
    ├── llm/                # Module for LLM interaction
    │   ├── __init__.py
    │   └── generator.py      # Generates post content
    └── posting/            # Modules for posting to platforms
        ├── __init__.py
        └── twitter_poster.py # Posts to X (Twitter)
        # ... (add other posters like linkedin_poster.py here)
```

## Setup

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/githubX.git # Replace with your repo URL
    cd githubX
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure `config.yaml`:**

    - Open the `config.yaml` file.
    - **Review and customize:**
      - `persona`: Define the voice/style for the LLM.
      - `llm.model`: Choose the Gemini model (e.g., `gemini-1.5-flash`).
      - `llm.default_prompt_template`: Modify the prompt if needed.
      - `data_sources`: Enable/disable sources (`enabled: true/false`). Ensure `_env_var` keys match the secrets you will create.
      - `posting`: Enable/disable posting targets. Set limits (`max_posts_per_run`, `sleep_between_posts`). Ensure `_env_var` keys match the secrets.
    - **Secret Names:** Pay close attention to the `_env_var` values (e.g., `username_env_var: GITHUB_USERNAME`). These tell the script which GitHub Secret to look for. You _must_ create secrets with these exact names in your GitHub repository settings.

5.  **Configure GitHub Secrets:**
    Go to your repository's `Settings` > `Secrets and variables` > `Actions`.
    Click `New repository secret` and add secrets corresponding to **all** the `_env_var` names defined in your `config.yaml` for enabled sources and targets. For the default config, you need:

    - `GITHUB_USERNAME`: Your GitHub username.
    - `USER_GITHUB_PAT`: Your GitHub Personal Access Token with `repo` and `read:user` scopes.
    - `GEMINI_API_KEY`: Your Google AI Studio API Key.
    - `X_API_KEY`: Your X App's API Key.
    - `X_API_SECRET`: Your X App's API Key Secret.
    - `X_ACCESS_TOKEN`: Your X App's Access Token.
    - `X_ACCESS_TOKEN_SECRET`: Your X App's Access Token Secret.

## Usage

The script is designed to be run automatically via the GitHub Actions workflow defined in `.github/workflows/daily_report.yml`.

- **Scheduled Run:** The workflow runs daily (default: 7:00 AM UTC). Edit the `cron` expression in the workflow file to change the schedule.
- **Manual Run:** Trigger the workflow manually from the Actions tab in your GitHub repository.
- **Configuration:** Modify `config.yaml` to change behavior (prompts, enabled sources/targets, limits, etc.) and commit the changes.

## Local Development (Optional)

1.  Ensure you have completed steps 1-3 of Setup.
2.  Create a `.env` file in the project root (this file is ignored by git).
3.  Add your secrets to the `.env` file in the format `KEY=VALUE` (use the **exact names** defined as `_env_var` in `config.yaml`).
    Example `.env`:
    ```
    GITHUB_USERNAME=your_github_username
    USER_GITHUB_PAT=ghp_...
    GEMINI_API_KEY=ai_...
    X_API_KEY=...
    X_API_SECRET=...
    X_ACCESS_TOKEN=...
    X_ACCESS_TOKEN_SECRET=...
    ```
4.  Modify `config.yaml` for local testing if needed (e.g., disable posting targets initially).
5.  Run the script from the project root:
    ```bash
    python main.py
    ```
    *(Note: The script uses `src.config_loader.get_secret` which reads from `os.environ`. GitHub Actions provides secrets as environment variables. For local runs, you need a mechanism to load `.env` into environment variables *before* the script runs. Tools like `python-dotenv` can do this, but currently, the script itself doesn't explicitly load `.env`. You might need to load it externally or modify the script slightly if you rely heavily on local runs.)*
