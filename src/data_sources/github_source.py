import sys
from datetime import datetime, timedelta, timezone
import github

# Định nghĩa cấu trúc dữ liệu chuẩn cho một hoạt động (ví dụ)
# Có thể dùng Pydantic hoặc class nếu muốn chặt chẽ hơn
Activity = dict[str, any] # Ví dụ: {source, timestamp, type, summary, details, url}

def get_activity(username: str, token: str, activity_format: str) -> list[Activity]:
    """Lấy hoạt động GitHub (commits) trong 24 giờ qua và chuẩn hóa kết quả."""
    print(f"[GitHub Source] Fetching activity for user: {username}")
    activities: list[Activity] = []
    if not username or not token:
        print("[GitHub Source] Error: Username or token not provided.", file=sys.stderr)
        return activities

    try:
        g = github.Github(token)
        user = g.get_user(username)
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        print(f"[GitHub Source] Checking events since {since.isoformat()}...")
        events = user.get_events()
        processed_commit_shas = set()

        for event in events:
            event_time = event.created_at.replace(tzinfo=timezone.utc)
            if event_time < since:
                break

            if event.type == 'PushEvent':
                if not hasattr(event, 'payload') or 'commits' not in event.payload:
                    continue

                repo_name = event.repo.name
                repo_full_name = event.repo.full_name
                commits = event.payload.get("commits", [])

                for commit in commits:
                    commit_sha = commit.get('sha')
                    if not commit_sha or commit_sha in processed_commit_shas:
                        continue

                    commit_message = commit.get('message', '').split('\n')[0]
                    processed_commit_shas.add(commit_sha)

                    # Tạo summary dựa trên format từ config
                    summary = activity_format.format(
                        repo=repo_name,
                        message=commit_message
                        # Thêm các placeholder khác nếu format cần
                    )

                    # Tạo dictionary hoạt động chuẩn hóa
                    activity_entry: Activity = {
                        "source": "github",
                        "timestamp": event_time, # Lưu thời gian sự kiện (hoặc commit time nếu muốn)
                        "type": "commit",
                        "summary": summary,
                        "details": {
                            "repo_name": repo_name,
                            "repo_full_name": repo_full_name,
                            "message": commit_message,
                            "sha": commit_sha
                        },
                        "url": f"https://github.com/{repo_full_name}/commit/{commit_sha}"
                    }
                    activities.append(activity_entry)
                    print(f"  [GitHub Source] Added commit from {repo_name}: {commit_message[:50]}...")

            # --- Thêm các loại sự kiện khác ở đây nếu cần --- 
            # Ví dụ: PRs, Issues, ... với cấu trúc chuẩn hóa tương tự

        if not activities:
            print("[GitHub Source] No relevant activity found in the last 24 hours.")
        else:
            print(f"[GitHub Source] Found {len(activities)} relevant activities.")

    except github.GithubException as e:
        # Phân tích lỗi cụ thể hơn nếu cần (ví dụ: BadCredentials, RateLimitExceeded)
        print(f"[GitHub Source] Error fetching activity: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[GitHub Source] An unexpected error occurred: {e}", file=sys.stderr)

    return activities

# Test function khi chạy trực tiếp (cần có file config.yaml và .env để test)
if __name__ == '__main__':
    print("Testing GitHub Source module...")
    # Đoạn này cần đọc config và secrets để chạy test độc lập
    # Ví dụ đơn giản hóa:
    # from dotenv import load_dotenv
    # import os
    # load_dotenv()
    # test_user = os.environ.get("GITHUB_USERNAME")
    # test_token = os.environ.get("USER_GITHUB_PAT")
    # test_format = "- Test commit on {repo}: {message}"
    # if test_user and test_token:
    #     results = get_activity(test_user, test_token, test_format)
    #     print(f"\nRetrieved {len(results)} activities:")
    #     for act in results:
    #         print(f"  - {act['summary']}")
    # else:
    #     print("Skipping test: Set GITHUB_USERNAME and USER_GITHUB_PAT in .env file")
    print("Please run the main script for full execution with config loading.")
