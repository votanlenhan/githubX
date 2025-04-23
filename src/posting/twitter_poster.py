import sys
import tweepy

def post_tweet(text: str, api_key: str, api_secret: str, access_token: str, access_token_secret: str) -> bool:
    """Đăng một tweet lên X (Twitter) sử dụng API v2."""
    if not text:
        print("[Twitter Poster] Error: No text provided to post.", file=sys.stderr)
        return False
    
    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("[Twitter Poster] Error: Missing Twitter API credentials.", file=sys.stderr)
        return False

    print(f"[Twitter Poster] Attempting to post tweet: {text[:100]}...")
    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        response = client.create_tweet(text=text)
        tweet_id = response.data['id']
        print(f"[Twitter Poster] Tweet posted successfully! ID: {tweet_id}")
        return True

    except tweepy.errors.TweepyException as e:
        print(f"[Twitter Poster] Error posting to X: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[Twitter Poster] An unexpected error occurred: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    print("Testing Twitter Poster module...")
    print("Please run the main script for full execution with config loading.")
