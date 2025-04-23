import sys
import time
from datetime import datetime, timezone
import importlib # Needed to dynamically import data sources
import random # Re-enable random import

# Import base modules
from src.config_loader import load_config, get_secret
from src.llm import generator
from src.posting import twitter_poster # Only twitter for now

def run_update():
    """Main coordinating function for the update process."""
    
    # --- Randomized Start Delay ---
    sleep_minutes = random.randint(0, 240) # Random delay between 0 and 240 minutes (4 hours)
    if sleep_minutes > 0:
      print(f"Sleeping for {sleep_minutes} minutes to randomize start time...")
      time.sleep(sleep_minutes * 60)
      print("Waking up and starting the process...")
    else:
      print("Starting process immediately (no random delay).")
    # -----------------------------

    print(f"=== Starting githubX Run at {datetime.now(timezone.utc).isoformat()} ===")

    # 1. Load Configuration
    config = load_config()
    if not config:
        print("Exiting due to configuration loading failure.", file=sys.stderr)
        return

    llm_config = config.get('llm', {})
    persona = config.get('persona', 'A developer sharing their journey.')
    gemini_api_key = get_secret("GEMINI_API_KEY") # Assume fixed env var name for LLM key

    if not gemini_api_key:
        print(f"Exiting because Gemini API Key (GEMINI_API_KEY) was not found.", file=sys.stderr)
        return

    all_generated_posts = [] # Collect posts from all sources here
    enabled_sources_config = config.get('data_sources', {})
    source_prompts = llm_config.get('source_prompts', {})

    # --- Mapping from config key to module name ---
    # Allows adding new sources more easily later
    source_module_map = {
        "github": "src.data_sources.github_source",
        "garmin": "src.data_sources.garmin_source",
        # Add other sources here, e.g., "strava": "src.data_sources.strava_source"
    }

    # 2. Fetch Data and Generate Posts per Source
    print("\n--- Processing Data Sources ---")
    for source_key, source_conf in enabled_sources_config.items():
        if source_conf.get('enabled'):
            print(f"\nProcessing source: {source_key}...")
            module_name = source_module_map.get(source_key)
            if not module_name:
                print(f"Warning: No module mapping found for enabled source key '{source_key}'. Skipping.", file=sys.stderr)
                continue

            try:
                source_module = importlib.import_module(module_name)
            except ModuleNotFoundError:
                print(f"Error: Could not import module '{module_name}' for source '{source_key}'. Make sure it exists. Skipping.", file=sys.stderr)
                continue
            except Exception as e:
                 print(f"Error importing module '{module_name}': {e}. Skipping source '{source_key}'.", file=sys.stderr)
                 continue

            # Get credentials based on config
            username_env_var = source_conf.get('username_env_var')
            password_env_var = source_conf.get('password_env_var') # For sources needing password
            pat_env_var = source_conf.get('pat_env_var') # For sources needing PAT

            username = get_secret(username_env_var) if username_env_var else None
            password = get_secret(password_env_var) if password_env_var else None
            pat = get_secret(pat_env_var) if pat_env_var else None

            activity_format = source_conf.get('activity_format', '- {summary}') # Default format

            # Call the source's get_activity function
            # Pass necessary credentials (adapt based on source needs)
            source_activities = []
            try:
                if source_key == 'github':
                    if username and pat: # GitHub needs username and PAT
                        source_activities = source_module.get_activity(username, pat, activity_format)
                    else:
                         print(f"Skipping {source_key} source due to missing username or PAT secret.", file=sys.stderr)
                elif source_key == 'garmin':
                    if username and password: # Garmin needs username and password
                         source_activities = source_module.get_activity(username, password, activity_format)
                    else:
                         print(f"Skipping {source_key} source due to missing username or password secret.", file=sys.stderr)
                # Add conditions for other sources here...
                else:
                     print(f"Warning: Don't know how to call get_activity for source '{source_key}'. Skipping.", file=sys.stderr)
            except Exception as e:
                 print(f"Error calling get_activity for {source_key}: {e}", file=sys.stderr)
                 # Continue to next source if one fails

            if source_activities:
                print(f"Found {len(source_activities)} activities from {source_key}.")
                # Get the specific prompt for this source
                specific_prompt = source_prompts.get(source_key)
                if not specific_prompt:
                    print(f"Warning: No specific prompt found for source '{source_key}' in config. Using default.", file=sys.stderr)
                    # Fallback to default handled inside generate_posts

                # Generate posts for this source's activities
                print(f"Generating content for {source_key} activities...")
                generated_posts = generator.generate_posts(
                    source_activities,
                    llm_config,
                    persona,
                    gemini_api_key,
                    specific_prompt_template=specific_prompt # Pass the specific prompt
                )
                if generated_posts:
                    print(f"Generated {len(generated_posts)} post(s) for {source_key}.")
                    all_generated_posts.extend(generated_posts)
                else:
                    print(f"LLM did not generate posts for {source_key}.")
            else:
                 print(f"No activities found for {source_key}.")


    # 3. Post Generated Content
    print("\n--- Posting Content ---")
    if not all_generated_posts:
        print("No posts were generated from any source. Nothing to post.")
    else:
        posting_config = config.get('posting', {})
        max_posts = posting_config.get('max_posts_per_run', 1)
        sleep_time = posting_config.get('sleep_between_posts', 10)
        enabled_targets = posting_config.get('targets', {})

        posts_to_send = all_generated_posts[:max_posts]
        print(f"Attempting to send {len(posts_to_send)} posts (out of {len(all_generated_posts)} generated).")
        posts_sent_count = 0

        if enabled_targets.get('twitter', {}).get('enabled'):
            print(f"Posting to Twitter...")
            twitter_conf = enabled_targets['twitter']
            tw_api_key = get_secret(twitter_conf.get('api_key_env_var'))
            tw_api_secret = get_secret(twitter_conf.get('api_secret_env_var'))
            tw_access_token = get_secret(twitter_conf.get('access_token_env_var'))
            tw_access_secret = get_secret(twitter_conf.get('access_token_secret_env_var'))

            if all([tw_api_key, tw_api_secret, tw_access_token, tw_access_secret]):
                for i, post_text in enumerate(posts_to_send):
                    print(f"Posting tweet {i+1}/{len(posts_to_send)}...")
                    success = twitter_poster.post_tweet(
                        post_text,
                        tw_api_key,
                        tw_api_secret,
                        tw_access_token,
                        tw_access_secret
                    )
                    if success:
                        posts_sent_count += 1
                        if posts_sent_count < len(posts_to_send):
                            print(f"Sleeping for {sleep_time} seconds...")
                            time.sleep(sleep_time)
                    else:
                        print(f"Failed to post tweet {i+1}. Continuing...")
            else:
                print("Skipping Twitter posting due to missing API credentials.", file=sys.stderr)
        else:
             print("Twitter posting target not enabled.")

        # Add logic for other posting targets here...

        print(f"\n--- Summary ---")
        print(f"Total posts generated across all sources: {len(all_generated_posts)}.")
        print(f"Attempted to send: {len(posts_to_send)}.")
        print(f"Successfully posted: {posts_sent_count}.")

    print(f"=== Run Finished at {datetime.now(timezone.utc).isoformat()} ===")

if __name__ == "__main__":
    run_update()