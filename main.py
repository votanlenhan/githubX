import sys
import time
from datetime import datetime, timezone

# Import các module từ thư mục src
from src.config_loader import load_config, get_secret
from src.data_sources import github_source # Sau này có thể import thêm garmin_source,...
from src.llm import generator
from src.posting import twitter_poster # Sau này có thể import thêm linkedin_poster,...

def run_update():
    """Hàm chính điều phối toàn bộ quy trình cập nhật."""
    print(f"=== Starting githubX Run at {datetime.now(timezone.utc).isoformat()} ===")

    # 1. Tải cấu hình
    config = load_config()
    if not config:
        # load_config đã in lỗi và thoát, nhưng để chắc chắn
        print("Exiting due to configuration loading failure.", file=sys.stderr)
        return

    all_activities = []
    enabled_sources = config.get('data_sources', {})

    # 2. Lấy dữ liệu từ các nguồn được kích hoạt
    print("\n--- Fetching Data ---")
    if enabled_sources.get('github', {}).get('enabled'):
        print("Fetching from GitHub...")
        github_conf = enabled_sources['github']
        gh_username = get_secret(github_conf.get('username_env_var'))
        gh_pat = get_secret(github_conf.get('pat_env_var'))
        gh_format = github_conf.get('activity_format', "- Repo {repo}: {message}") # Format mặc định

        if gh_username and gh_pat:
            github_activities = github_source.get_activity(gh_username, gh_pat, gh_format)
            all_activities.extend(github_activities)
        else:
            print("Skipping GitHub source due to missing username or PAT secret.", file=sys.stderr)

    # --- Thêm logic cho các nguồn dữ liệu khác ở đây ---
    # Ví dụ:
    # if enabled_sources.get('garmin', {}).get('enabled'):
    #     print("Fetching from Garmin...")
    #     garmin_conf = enabled_sources['garmin']
    #     # ... lấy secrets và gọi garmin_source.get_activity(...) ...
    #     # all_activities.extend(garmin_activities)

    if not all_activities:
        print("\nNo activities found from any enabled source. Nothing to post.")
        print(f"=== Run Finished at {datetime.now(timezone.utc).isoformat()} ===")
        return

    # Sắp xếp hoạt động theo thời gian (tùy chọn, nhưng có thể giúp LLM hiểu ngữ cảnh tốt hơn)
    all_activities.sort(key=lambda x: x.get('timestamp', datetime.min.replace(tzinfo=timezone.utc)))
    print(f"\nTotal activities fetched: {len(all_activities)}")

    # 3. Tạo nội dung bài đăng bằng LLM
    print("\n--- Generating Content ---")
    llm_config = config.get('llm', {})
    persona = config.get('persona', 'A developer sharing their journey.') # Persona mặc định
    gemini_api_key_env_var = "GEMINI_API_KEY" # Giả sử tên biến môi trường cố định cho API key LLM
    gemini_api_key = get_secret(gemini_api_key_env_var)

    generated_posts = []
    if gemini_api_key:
        generated_posts = generator.generate_posts(all_activities, llm_config, persona, gemini_api_key)
    else:
        print(f"Skipping content generation because secret '{gemini_api_key_env_var}' was not found.", file=sys.stderr)

    if not generated_posts:
        print("\nLLM did not generate any posts. Nothing to post.")
        print(f"=== Run Finished at {datetime.now(timezone.utc).isoformat()} ===")
        return

    # 4. Đăng bài lên các nền tảng được kích hoạt
    print("\n--- Posting Content ---")
    posting_config = config.get('posting', {})
    max_posts = posting_config.get('max_posts_per_run', 1) # Mặc định đăng 1 bài
    sleep_time = posting_config.get('sleep_between_posts', 10)
    enabled_targets = posting_config.get('targets', {})
    
    posts_sent_count = 0

    # Chỉ lấy số lượng bài đăng tối đa cần gửi
    posts_to_send = generated_posts[:max_posts]

    if enabled_targets.get('twitter', {}).get('enabled'):
        print(f"Attempting to post {len(posts_to_send)} tweet(s) to Twitter...")
        twitter_conf = enabled_targets['twitter']
        tw_api_key = get_secret(twitter_conf.get('api_key_env_var'))
        tw_api_secret = get_secret(twitter_conf.get('api_secret_env_var'))
        tw_access_token = get_secret(twitter_conf.get('access_token_env_var'))
        tw_access_secret = get_secret(twitter_conf.get('access_token_secret_env_var'))

        if all([tw_api_key, tw_api_secret, tw_access_token, tw_access_secret]):
            for i, post_text in enumerate(posts_to_send):
                success = twitter_poster.post_tweet(
                    post_text,
                    tw_api_key,
                    tw_api_secret,
                    tw_access_token,
                    tw_access_secret
                )
                if success:
                    posts_sent_count += 1
                    # Nghỉ giữa các lần đăng nếu còn bài và chưa phải bài cuối
                    if posts_sent_count < len(posts_to_send):
                        print(f"Sleeping for {sleep_time} seconds...")
                        time.sleep(sleep_time)
                else:
                    print(f"Failed to post tweet {i+1}. Continuing...") 
                    # Có thể thêm logic để dừng nếu có lỗi nghiêm trọng

        else:
            print("Skipping Twitter posting due to missing API credentials.", file=sys.stderr)

    # --- Thêm logic cho các nền tảng đăng bài khác ở đây ---
    # Ví dụ:
    # if enabled_targets.get('linkedin', {}).get('enabled'):
    #     print("Attempting to post to LinkedIn...")
    #     # ... lấy secrets và gọi linkedin_poster.post(...) ...

    print(f"\n--- Summary ---")
    print(f"Fetched {len(all_activities)} activities.")
    print(f"Generated {len(generated_posts)} posts (attempted to send {len(posts_to_send)})." )
    print(f"Successfully posted {posts_sent_count} times.")
    print(f"=== Run Finished at {datetime.now(timezone.utc).isoformat()} ===")


if __name__ == "__main__":
    run_update()