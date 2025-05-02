import sys
import time
from datetime import datetime, timezone
import importlib # Needed to dynamically import data sources
# import random # Temporarily commented out for testing

# Import base modules
from src.config_loader import load_config, get_secret
# Import the specific functions needed
from src.llm.generator import generate_posts, generate_follow_up_comment
from src.posting import twitter_poster # Only twitter for now

def run_update():
    """Main coordinating function for the update process."""
    
    # # --- Randomized Start Delay (Temporarily Disabled for Testing) ---
    # sleep_minutes = random.randint(0, 240) # Random delay between 0 and 240 minutes (4 hours)
    # if sleep_minutes > 0:
    #   print(f"Sleeping for {sleep_minutes} minutes to randomize start time...")
    #   time.sleep(sleep_minutes * 60)
    #   print("Waking up and starting the process...")
    # else:
    #   print("Starting process immediately (no random delay).")
    # # ------------------------------------------------------------------

    print(f"=== Starting githubX Run at {datetime.now(timezone.utc).isoformat()} ===")

    # 1. Load Configuration
    config = load_config()
    # ---- DEBUG: Print config['llm'] immediately after loading ----
    # print(f"[DEBUG] config.get('llm') right after load_config: {config.get('llm')}") # No longer needed
    # ----------------------------------------------------------
    if not config:
        print("Exiting due to configuration loading failure.", file=sys.stderr)
        return

    # --- Get LLM config ONCE ---
    llm_config = config.get('llm', {})
    # print(f"[DEBUG] llm_config obtained once: {llm_config}") # Debug this once - No longer needed
    # -------------------------

    persona = config.get('persona', 'A developer sharing their journey.')
    gemini_api_key = get_secret("GEMINI_API_KEY") # Assume fixed env var name for LLM key

    if not gemini_api_key:
        print(f"Exiting because Gemini API Key (GEMINI_API_KEY) was not found.", file=sys.stderr)
        return

    # ---- Data structure to hold generated content and its context ----
    # List of {"source": str, "tweet_text": str, "first_activity": dict | None}
    generated_content_list = []
    # -------------------------------------------------------------------

    enabled_sources_config = config.get('data_sources', {})
    # --- Use llm_config obtained earlier --- 
    source_prompts = llm_config.get('source_prompts', {})
    # ---------------------------------------
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
            first_activity_for_source = None # Store the first activity for follow-up context
            try:
                if source_key == 'github':
                    if username and pat: # GitHub needs username and PAT
                        source_activities = source_module.get_activity(username, pat, activity_format)
                    else:
                         print(f"Skipping {source_key} source due to missing username or PAT secret.", file=sys.stderr)
                elif source_key == 'garmin':
                    if username and password: # Garmin needs username and password
                         # ---- NEW: Pass daily_summary_format to get_activity ----
                         daily_format = source_conf.get('daily_summary_format')
                         source_activities = source_module.get_activity(
                             username,
                             password,
                             activity_format,
                             daily_summary_format=daily_format
                         )
                         # ----------------------------------------------------------
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
                first_activity_for_source = source_activities[0] # Get the first activity for context

                # --- Determine the correct prompt key based on activity source ---
                prompt_key_to_use = source_key # Default to the main source key ('github', 'garmin')
                if first_activity_for_source.get('source') == 'garmin_daily':
                    prompt_key_to_use = 'garmin_daily' # Use the specific key for daily summary
                # ------------------------------------------------------------------
                
                # --- Use the determined prompt key to get the template ---
                specific_prompt = source_prompts.get(prompt_key_to_use)
                # -------------------------------------------------------
                if not specific_prompt:
                    print(f"Warning: No specific prompt found for source key '{prompt_key_to_use}' in config. Using default.", file=sys.stderr)
                    # Fallback to default handled inside generate_posts

                # Generate posts for this source's activities
                print(f"Generating content for {source_key} activities...")
                # Assume generate_posts returns a LIST of tweet strings
                generated_posts_texts = generate_posts(
                    source_activities,
                    llm_config, # Pass the whole llm_config
                    persona,
                    gemini_api_key,
                    specific_prompt_template=specific_prompt # Pass the specific prompt
                )

                if generated_posts_texts:
                    print(f"Generated {len(generated_posts_texts)} post text(s) for {source_key}.")
                    # --- Store generated text with context ---
                    for text in generated_posts_texts:
                        generated_content_list.append({
                            "source": prompt_key_to_use, # Use the specific source (e.g., garmin_daily)
                            "tweet_text": text,
                            "first_activity": first_activity_for_source # Associate with the first activity
                        })
                    # ----------------------------------------
                else:
                    print(f"LLM did not generate posts for {source_key}.")
            else:
                 print(f"No activities found for {source_key}.")


    # 3. Post Generated Content (with Follow-up Logic)
    print("\n--- Posting Content ---")
    if not generated_content_list:
        print("No posts were generated from any source. Nothing to post.")
    else:
        posting_config = config.get('posting', {})
        twitter_config = posting_config.get('targets', {}).get('twitter', {})
        max_posts = posting_config.get('max_posts_per_run', 1)
        sleep_time = posting_config.get('sleep_between_posts', 90) # Get the sleep time
        enable_follow_up = twitter_config.get('enable_follow_up', False)
        
        # --- Corrected access to follow_up_prompts (nested inside source_prompts) --- 
        follow_up_prompts = llm_config.get('source_prompts', {}).get('follow_up_prompts', {})
        # --------------------------------------------------------------------------
        
        # ---- DEBUG: Check the correctly loaded follow-up prompts ----
        # print(f"[DEBUG] Follow-up prompts dictionary: {follow_up_prompts}") # No longer needed
        # -----------------------------------------------

        content_to_send = generated_content_list[:max_posts]
        print(f"Attempting to send {len(content_to_send)} primary posts (out of {len(generated_content_list)} generated).")
        posts_sent_count = 0

        if twitter_config.get('enabled'):
            print(f"Posting to Twitter...")
            tw_api_key = get_secret(twitter_config.get('api_key_env_var'))
            tw_api_secret = get_secret(twitter_config.get('api_secret_env_var'))
            tw_access_token = get_secret(twitter_config.get('access_token_env_var'))
            tw_access_secret = get_secret(twitter_config.get('access_token_secret_env_var'))

            if all([tw_api_key, tw_api_secret, tw_access_token, tw_access_secret]):
                for i, content_item in enumerate(content_to_send):
                    print(f"\nProcessing post {i+1}/{len(content_to_send)}...")
                    original_tweet_text = content_item["tweet_text"]
                    source_key = content_item["source"]
                    first_activity = content_item["first_activity"]

                    # --- Post Original Tweet ---
                    print(f"Posting original tweet for {source_key}...")
                    original_tweet_id = twitter_poster.post_tweet(
                        original_tweet_text,
                        tw_api_key, tw_api_secret, tw_access_token, tw_access_secret
                    )

                    if original_tweet_id:
                        posts_sent_count += 1
                        print(f"Original tweet for {source_key} posted successfully (ID: {original_tweet_id}).")

                        # --- Attempt Follow-up Comment ---
                        if enable_follow_up and first_activity:
                            # ---- Select follow-up prompt based on the *actual* source_key ('github', 'garmin', or 'garmin_daily') ----
                            print(f"[DEBUG] Attempting follow-up for source_key: '{source_key}'")
                            follow_up_prompt = follow_up_prompts.get(source_key)
                            print(f"[DEBUG] Result of follow_up_prompts.get('{source_key}'): {follow_up_prompt is not None}")
                            # ------------------------------------------------------------------------------------------------
                            if follow_up_prompt:
                                print(f"Generating follow-up comment for {source_key} tweet...")
                                comment_text = generate_follow_up_comment(
                                    original_tweet_text=original_tweet_text,
                                    activity=first_activity,
                                    llm_config=llm_config, # Pass the whole llm_config
                                    persona=persona, # Pass persona just in case
                                    gemini_api_key=gemini_api_key,
                                    specific_follow_up_prompt=follow_up_prompt
                                )
                                if comment_text:
                                    print(f"Generated follow-up: {comment_text[:100]}...")
                                    # --- Restore delay before posting reply ---
                                    follow_up_delay = 10 # seconds
                                    print(f"Waiting {follow_up_delay}s before posting follow-up...")
                                    time.sleep(follow_up_delay)
                                    # ------------------------------------------

                                    print(f"Posting follow-up comment for {source_key} tweet {original_tweet_id}...")
                                    reply_tweet_id = twitter_poster.post_tweet(
                                        comment_text,
                                        tw_api_key, tw_api_secret, tw_access_token, tw_access_secret,
                                        in_reply_to_tweet_id=original_tweet_id # Pass original ID
                                    )
                                    if not reply_tweet_id:
                                        print(f"Warning: Failed to post follow-up comment for tweet {original_tweet_id}.", file=sys.stderr)
                                else:
                                    print(f"LLM did not generate a follow-up comment for {source_key}.")
                            else:
                                print(f"No follow-up prompt found for source '{source_key}'. Skipping follow-up.")
                        else:
                             print(f"Follow-up comments disabled or no activity data for {source_key}. Skipping.")
                        # ------------------------------

                    else:
                        print(f"Failed to post original tweet {i+1} for {source_key}. Continuing...")

                    # --- Restore sleep between PRIMARY posts --- 
                    # Check if more primary posts are needed AND if it's not the very last one in the loop
                    if posts_sent_count < len(content_to_send) and i < len(content_to_send) - 1: 
                       print(f"Sleeping for {sleep_time} seconds before next primary post...")
                       time.sleep(sleep_time)
                    # ---------------------------------------------
                    
            else:
                print("Skipping Twitter posting due to missing API credentials.", file=sys.stderr)
        else:
             print("Twitter posting target not enabled.")

        print(f"\n--- Summary ---")
        print(f"Total posts generated across all sources: {len(generated_content_list)}.")
        print(f"Attempted to send: {len(content_to_send)} primary posts.")
        print(f"Successfully posted: {posts_sent_count} primary posts.") # Only count primary posts

    print(f"=== Run Finished at {datetime.now(timezone.utc).isoformat()} ===")

if __name__ == "__main__":
    run_update()