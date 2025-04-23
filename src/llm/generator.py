import sys
import google.generativeai as genai
from ..config_loader import get_secret # Import từ cùng package cấp cao hơn

# Định nghĩa lại kiểu dữ liệu chuẩn (hoặc import từ một module chung)
Activity = dict[str, any]

def generate_posts(all_activities: list[Activity], llm_config: dict, persona: str, gemini_api_key: str) -> list[str]:
    """Tạo nội dung bài đăng mạng xã hội dựa trên danh sách các hoạt động đã chuẩn hóa."""
    if not all_activities:
        print("[LLM Generator] No activities provided to generate posts.")
        return []

    print("[LLM Generator] Generating post(s) using LLM...")

    model_name = llm_config.get('model', 'gemini-pro')
    prompt_template = llm_config.get('default_prompt_template')

    if not gemini_api_key:
        print("[LLM Generator] Error: Gemini API key not found.", file=sys.stderr)
        return []
    if not prompt_template:
        print("[LLM Generator] Error: Prompt template not found in config.", file=sys.stderr)
        return []

    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel(model_name)

        activity_summary_lines = [act.get('summary', 'Hoạt động không rõ') for act in all_activities]
        activity_summary_str = "\n".join(activity_summary_lines)

        prompt = prompt_template.format(
            persona=persona,
            activity_summary=activity_summary_str
        )

        print(f"\n--- [LLM Generator] Sending Prompt ---
{prompt}
-------------------------------------\n")

        response = model.generate_content(prompt)
        generated_text = response.text.strip()
        
        if not generated_text:
             print("[LLM Generator] Error: LLM generated empty text.", file=sys.stderr)
             return []

        print(f"[LLM Generator] Generated text block:\n{generated_text}\n-------------------------------------")

        # Tách thành nhiều tweets
        potential_tweets = [t.strip() for t in generated_text.split('\n\n') if t.strip()]
        
        final_tweets = []
        for tweet in potential_tweets:
            if len(tweet) > 280:
                print(f"[LLM Generator] Warning: Truncating generated tweet exceeding 280 chars: {tweet[:50]}...")
                last_space = tweet[:277].rfind(' ')
                if last_space != -1:
                    final_tweets.append(tweet[:last_space] + "...")
                else:
                    final_tweets.append(tweet[:277] + "...")
            else:
                final_tweets.append(tweet)
        
        if not final_tweets:
            print("[LLM Generator] No valid tweets generated after splitting/validation.")
            return []
            
        print(f"[LLM Generator] Successfully generated {len(final_tweets)} tweet(s).")
        return final_tweets

    except AttributeError as e:
        if 'text' not in str(e) and hasattr(response, 'prompt_feedback'):
            print(f"[LLM Generator] Error: Content generation likely blocked. Feedback: {response.prompt_feedback}", file=sys.stderr)
        else:
             print(f"[LLM Generator] Error processing LLM response: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[LLM Generator] Error generating report with LLM: {e}", file=sys.stderr)
        return []

# Test function
if __name__ == '__main__':
    print("Testing LLM Generator module...")
    # Cần mock data và config để test độc lập
    # mock_activities = [
    #     {"source": "github", "summary": "- Đã làm việc trên repo CoolProject: Thêm tính năng mới"},
    #     {"source": "github", "summary": "- Đã làm việc trên repo AnotherOne: Sửa lỗi hiển thị"},
    #     # {"source": "garmin", "summary": "- Hoàn thành bài tập chạy bộ dài 5 km."}
    # ]
    # mock_llm_config = {
    #     "model": "gemini-1.5-flash",
    #     "default_prompt_template": "Bạn là {persona}. Hoạt động: {activity_summary}. Tweet:"
    # }
    # mock_persona = "Người thử nghiệm"
    # # Cần lấy API Key từ .env
    # from dotenv import load_dotenv
    # import os
    # load_dotenv()
    # test_api_key = os.environ.get("GEMINI_API_KEY") 
    # if test_api_key:
    #      tweets = generate_posts(mock_activities, mock_llm_config, mock_persona, test_api_key)
    #      print(f"\nGenerated {len(tweets)} tweets:")
    #      for i, tweet in enumerate(tweets):
    #          print(f"Tweet {i+1}: {tweet}")
    # else:
    #     print("Skipping test: Set GEMINI_API_KEY in .env file")
    print("Please run the main script for full execution with config loading.")

