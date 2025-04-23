import sys
import tweepy
import logging # Use logging for better messages

logger = logging.getLogger(__name__)

# Updated function to return tweet ID and accept reply ID
def post_tweet(
    text: str,
    api_key: str,
    api_secret: str,
    access_token: str,
    access_token_secret: str,
    in_reply_to_tweet_id: str | None = None, # New optional parameter
) -> str | None: # Return tweet ID (str) or None on failure
    """Posts a tweet (or reply) to X (Twitter) using API v2."""
    if not text:
        logger.error("[Twitter Poster] No text provided to post.")
        return None

    if not all([api_key, api_secret, access_token, access_token_secret]):
        logger.error("[Twitter Poster] Missing Twitter API credentials.")
        return None

    # Prepare tweet parameters
    tweet_params = {"text": text}
    log_action = "tweet"
    if in_reply_to_tweet_id:
        tweet_params["reply"] = {"in_reply_to_tweet_id": in_reply_to_tweet_id}
        log_action = f"reply to {in_reply_to_tweet_id}"

    logger.info(f"[Twitter Poster] Attempting to post {log_action}: {text[:100]}...")
    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
        # Use **tweet_params to pass parameters dynamically
        response = client.create_tweet(**tweet_params)
        tweet_id = response.data["id"]
        logger.info(f"[Twitter Poster] {log_action.capitalize()} posted successfully! ID: {tweet_id}")
        return tweet_id # Return the ID of the newly created tweet

    except tweepy.errors.TweepyException as e:
        logger.error(f"[Twitter Poster] Error posting {log_action} to X: {e}")
        return None
    except Exception as e:
        logger.error(f"[Twitter Poster] An unexpected error occurred posting {log_action}: {e}")
        return None

if __name__ == '__main__':
    print("Testing Twitter Poster module...")
    print("Please run the main script for full execution with config loading.")
