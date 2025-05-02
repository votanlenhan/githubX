import sys
import google.generativeai as genai
from ..config_loader import get_secret # Import từ cùng package cấp cao hơn

# Định nghĩa lại kiểu dữ liệu chuẩn (hoặc import từ một module chung)
Activity = dict[str, any]

def generate_posts(all_activities: list[Activity], llm_config: dict, persona: str, gemini_api_key: str, specific_prompt_template: str | None = None) -> list[str]:
    """Tạo nội dung bài đăng mạng xã hội dựa trên danh sách các hoạt động đã chuẩn hóa."""
    if not all_activities:
        print("[LLM Generator] No activities provided to generate posts.")
        return []

    print("[LLM Generator] Generating post(s) using LLM...")

    model_name = llm_config.get('model', 'gemini-pro')
    prompt_template_to_use = specific_prompt_template if specific_prompt_template else llm_config.get('default_prompt_template')

    if not gemini_api_key:
        print("[LLM Generator] Error: Gemini API key not found.", file=sys.stderr)
        return []
    if not prompt_template_to_use:
        print("[LLM Generator] Error: No valid prompt template found (neither specific nor default in config).", file=sys.stderr)
        return []

    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel(model_name)

        activity_summary_lines = [act.get('summary', 'Activity details unclear') for act in all_activities]
        activity_summary_str = "\n".join(activity_summary_lines)

        prompt = prompt_template_to_use.format(
            persona=persona,
            activity_summary=activity_summary_str
        )

        print(f"""
--- [LLM Generator] Sending Prompt ---
{prompt}
-------------------------------------
""")

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
        # --- Enhanced Error Logging ---
        error_message = f"[LLM Generator] Error generating report with LLM: {e}"
        try:
            # Attempt to access prompt_feedback even in generic exception
            if hasattr(response, 'prompt_feedback'):
                error_message += f" | Feedback: {response.prompt_feedback}"
        except NameError: # Handle case where 'response' might not be defined yet
            pass 
        print(error_message, file=sys.stderr)
        # -----------------------------
        return []

# ---- NEW Function for Follow-up Comments ----
def generate_follow_up_comment(
    original_tweet_text: str,
    activity: Activity, # Pass the single activity dictionary
    llm_config: dict,
    persona: str, # Persona might not be needed if prompt is specific enough
    gemini_api_key: str,
    specific_follow_up_prompt: str | None = None,
) -> str | None: # Return single comment string or None
    """Generates a follow-up comment using the LLM."""
    # Re-import logger or pass it if defined globally earlier
    import logging
    logger = logging.getLogger(__name__)

    if not original_tweet_text or not activity or not specific_follow_up_prompt:
        logger.error("[LLM Generator] Missing data for generating follow-up comment.")
        return None

    logger.info("[LLM Generator] Generating follow-up comment...")

    model_name = llm_config.get('model', 'gemini-1.5-flash') # Use consistent model

    if not gemini_api_key:
        logger.error("[LLM Generator] Error: Gemini API key not found.")
        return None

    try:
        # Need to re-import or ensure genai is available
        import google.generativeai as genai 
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel(model_name)

        # Extract necessary details for the prompt
        activity_summary = activity.get('summary', 'Details unavailable')
        activity_url = activity.get('url', '') # Get URL if available

        # Format the specific follow-up prompt
        prompt = specific_follow_up_prompt.format(
            original_tweet_text=original_tweet_text,
            activity_summary=activity_summary, # The formatted summary string
            activity_url=activity_url,
            persona=persona # Include persona if needed by the prompt
        )

        logger.info(f"""
--- [LLM Generator] Sending Follow-up Prompt ---
{prompt}
---------------------------------------------
""")

        response = model.generate_content(prompt)
        generated_comment = response.text.strip()

        if not generated_comment:
             logger.error("[LLM Generator] Error: LLM generated empty follow-up comment.")
             return None

        # Basic length check for comment (though prompts should handle it)
        if len(generated_comment) > 280:
             logger.warning("[LLM Generator] Truncating generated comment exceeding 280 chars.")
             # Simple truncation, can be improved
             generated_comment = generated_comment[:277] + "..."

        logger.info(f"[LLM Generator] Generated follow-up comment: {generated_comment[:100]}...")
        return generated_comment

    except KeyError as e:
        logger.error(f"[LLM Generator] Error formatting follow-up prompt - Missing key: {e}", exc_info=True)
        return None
    except AttributeError as e:
         if 'text' not in str(e) and hasattr(response, 'prompt_feedback'):
             logger.error(f"[LLM Generator] Error: Follow-up generation likely blocked. Feedback: {response.prompt_feedback}")
         else:
              logger.error(f"[LLM Generator] Error processing LLM response for follow-up: {e}", exc_info=True)
         return None
    except Exception as e:
        # --- Enhanced Error Logging for Follow-up ---
        error_message = f"[LLM Generator] Error generating follow-up comment with LLM: {e}"
        try:
             # Attempt to access prompt_feedback even in generic exception
            if hasattr(response, 'prompt_feedback'):
                error_message += f" | Feedback: {response.prompt_feedback}"
        except NameError:
            pass
        logger.error(error_message, exc_info=True)
        # ----------------------------------------
        return None
# -------------------------------------------

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

