"""Module for fetching Garmin Connect activity using garminconnect library."""

import sys
import logging
from datetime import datetime, timedelta, timezone
import math # Add math for potential calculations like sleep hours

# Attempt to import garminconnect, handle if not installed
try:
    from garminconnect import (
        Garmin,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
        GarminConnectAuthenticationError
    )
except ModuleNotFoundError:
    print("Error: The 'garminconnect' library is required for Garmin integration.", file=sys.stderr)
    print("Please install it: pip install garminconnect", file=sys.stderr)
    # Allow the placeholder function to exist so main.py doesn't crash on import
    Garmin = None # Set Garmin to None if import fails

# Define the standard Activity structure
Activity = dict[str, any]

# Configure logging for garminconnect (optional, but helpful for debugging)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Helper function to format seconds ---
def format_duration(seconds):
    if seconds is None:
        return "N/A"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"

def get_activity(username: str | None, password: str | None, activity_format: str) -> list[Activity]:
    """
    Fetches recent Garmin activities (last 24 hours) and related daily stats/sleep
    using the garminconnect library.
    """
    activities: list[Activity] = []
    if not Garmin: # Check if library import failed
        print("[Garmin Source] Exiting because garminconnect library is not available.", file=sys.stderr)
        return activities
        
    if not username or not password:
        print("[Garmin Source] Error: Username or password not provided.", file=sys.stderr)
        return activities

    print(f"[Garmin Source] Attempting to fetch activity for user: {username}")
    
    client = None # Initialize client to None
    try:
        # Initialize Garmin client
        client = Garmin(username, password)
        client.login()
        print("[Garmin Source] Login successful.")

        # Define time range (e.g., last 24 hours)
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=1)
        print(f"[Garmin Source] Fetching data for date range: {start_date} to {end_date}...")

        # --- NEW: Fetch Daily Stats and Sleep Data for the end_date ---
        daily_stats = None
        sleep_data = None
        daily_context = {}
        try:
            print(f"[Garmin Source] Fetching daily stats for {end_date.isoformat()}...")
            daily_stats = client.get_stats(end_date.isoformat())
            if daily_stats:
                 print("[Garmin Source] Daily stats fetched successfully.")
                 daily_context['daily_steps'] = daily_stats.get('totalSteps', "N/A")
                 daily_context['stress_qualifier'] = daily_stats.get('stressQualifier', "N/A").replace('_', ' ').title() # Example: HIGH_STRESS -> High Stress
                 daily_context['avg_stress_level'] = daily_stats.get('averageStressLevel', "N/A") # Usually -1 if not worn, -2 if not available? Check API. Use qualifier instead?
                 daily_context['resting_hr'] = daily_stats.get('restingHeartRate', "N/A")
                 daily_context['body_battery_charged'] = daily_stats.get('bodyBatteryChargedValue', "N/A")
                 daily_context['body_battery_drained'] = daily_stats.get('bodyBatteryDrainedValue', "N/A")
                 # Add more stats if needed: totalDistanceMeters, highlyActiveSeconds, floorsAscended/Descended etc.
            else:
                print(f"[Garmin Source] No daily stats found for {end_date.isoformat()}.")

        except Exception as e:
             print(f"[Garmin Source] Error fetching daily stats: {e}", file=sys.stderr)
             # Set defaults if fetch fails
             daily_context['daily_steps'] = "N/A"
             daily_context['stress_qualifier'] = "N/A"
             daily_context['avg_stress_level'] = "N/A"
             daily_context['resting_hr'] = "N/A"
             daily_context['body_battery_charged'] = "N/A"
             daily_context['body_battery_drained'] = "N/A"

        try:
            print(f"[Garmin Source] Fetching sleep data for {end_date.isoformat()}...")
            # Note: Sleep data might correspond to the *night leading into* end_date
            sleep_data = client.get_sleep_data(end_date.isoformat())
            if sleep_data and 'dailySleepDTO' in sleep_data:
                 print("[Garmin Source] Sleep data fetched successfully.")
                 sleep_dto = sleep_data['dailySleepDTO']
                 total_sleep_sec = sleep_dto.get('sleepTimeSeconds')
                 deep_sleep_sec = sleep_dto.get('deepSleepSeconds')
                 rem_sleep_sec = sleep_dto.get('remSleepSeconds')
                 light_sleep_sec = sleep_dto.get('lightSleepSeconds')
                 awake_sleep_sec = sleep_dto.get('awakeSleepSeconds')

                 daily_context['sleep_duration_hr'] = round(total_sleep_sec / 3600, 1) if total_sleep_sec is not None else "N/A"
                 daily_context['sleep_duration_formatted'] = format_duration(total_sleep_sec)
                 daily_context['deep_sleep_percent'] = round((deep_sleep_sec / total_sleep_sec) * 100) if deep_sleep_sec is not None and total_sleep_sec else "N/A"
                 daily_context['rem_sleep_percent'] = round((rem_sleep_sec / total_sleep_sec) * 100) if rem_sleep_sec is not None and total_sleep_sec else "N/A"
                 daily_context['light_sleep_percent'] = round((light_sleep_sec / total_sleep_sec) * 100) if light_sleep_sec is not None and total_sleep_sec else "N/A"
                 daily_context['awake_duration_formatted'] = format_duration(awake_sleep_sec)
                 daily_context['sleep_score'] = sleep_dto.get('sleepScores', {}).get('overall', {}).get('value', "N/A") # Nested dict access
            else:
                 print(f"[Garmin Source] No sleep data found for {end_date.isoformat()}.")
                 # Set defaults if no sleep data
                 daily_context['sleep_duration_hr'] = "N/A"
                 daily_context['sleep_duration_formatted'] = "N/A"
                 daily_context['deep_sleep_percent'] = "N/A"
                 daily_context['rem_sleep_percent'] = "N/A"
                 daily_context['light_sleep_percent'] = "N/A"
                 daily_context['awake_duration_formatted'] = "N/A"
                 daily_context['sleep_score'] = "N/A"

        except Exception as e:
            print(f"[Garmin Source] Error fetching sleep data: {e}", file=sys.stderr)
            # Set defaults if fetch fails
            daily_context['sleep_duration_hr'] = "N/A"
            daily_context['sleep_duration_formatted'] = "N/A"
            daily_context['deep_sleep_percent'] = "N/A"
            daily_context['rem_sleep_percent'] = "N/A"
            daily_context['light_sleep_percent'] = "N/A"
            daily_context['awake_duration_formatted'] = "N/A"
            daily_context['sleep_score'] = "N/A"

        print(f"[Garmin Source] Daily Context prepared: {daily_context}")
        # ---------------------------------------------------------

        # Fetch activities (adjust limit as needed)
        print(f"[Garmin Source] Fetching activities from {start_date} to {end_date}...")
        garmin_activities = client.get_activities_by_date(
            start_date.isoformat(),
            end_date.isoformat()
            # Can add activity_type here, e.g., activitytype="running"
        )

        if not garmin_activities:
            print("[Garmin Source] No activities found in the specified date range.")
            # No need to return here, finally block will handle logout
        else:
            print(f"[Garmin Source] Found {len(garmin_activities)} activities. Processing...")
            # Process fetched activities
            for activity in garmin_activities:
                # Extract relevant details (adjust keys based on garminconnect output)
                activity_id = activity.get('activityId')
                activity_type = activity.get('activityType', {}).get('typeKey', 'unknown')
                start_time_str = activity.get('startTimeGMT')
                distance_meters = activity.get('distance')
                duration_seconds = activity.get('duration')
                # --- Attempt to extract additional metrics ---
                avg_hr = activity.get('averageHR')
                max_hr = activity.get('maxHR')
                calories = activity.get('calories')
                # -------------------------------------------

                try:
                    start_time = datetime.fromisoformat(start_time_str.replace(" ", "T") + "+00:00")
                except (TypeError, ValueError):
                    start_time = datetime.now(timezone.utc)

                distance_km = (distance_meters / 1000.0) if distance_meters else 0.0

                summary = "Unknown activity"
                try:
                    # Use a dictionary for formatting to handle missing keys gracefully
                    format_data = {
                        'activity_type': activity_type.replace('_', ' ').title(),
                        'distance': distance_km,
                        'duration': duration_seconds,
                        'duration_formatted': format_duration(duration_seconds),
                        'avg_hr': avg_hr if avg_hr is not None else "N/A",
                        'max_hr': max_hr if max_hr is not None else "N/A",
                        'calories': int(calories) if calories is not None else "N/A",
                        # --- Add NEW daily context placeholders ---
                        'daily_steps': daily_context.get('daily_steps', "N/A"),
                        'sleep_duration_hr': daily_context.get('sleep_duration_hr', "N/A"),
                        'sleep_duration_formatted': daily_context.get('sleep_duration_formatted', "N/A"),
                        'deep_sleep_percent': daily_context.get('deep_sleep_percent', "N/A"),
                        'rem_sleep_percent': daily_context.get('rem_sleep_percent', "N/A"),
                        'light_sleep_percent': daily_context.get('light_sleep_percent', "N/A"),
                        'awake_duration_formatted': daily_context.get('awake_duration_formatted', "N/A"),
                        'sleep_score': daily_context.get('sleep_score', "N/A"),
                        'stress_qualifier': daily_context.get('stress_qualifier', "N/A"),
                        'avg_stress_level': daily_context.get('avg_stress_level', "N/A"),
                        'resting_hr': daily_context.get('resting_hr', "N/A"),
                        'body_battery_charged': daily_context.get('body_battery_charged', "N/A"),
                        'body_battery_drained': daily_context.get('body_battery_drained', "N/A"),
                        # ---------------------------------------
                    }
                    summary = activity_format.format(**format_data)
                except KeyError as e:
                    print(f"[Garmin Source] Warning: Key '{e}' not found...", file=sys.stderr)
                except Exception as e:
                    print(f"[Garmin Source] Warning: Error formatting summary...: {e}", file=sys.stderr)
                
                activity_entry: Activity = {
                    "source": "garmin",
                    "timestamp": start_time,
                    "type": activity_type,
                    "summary": summary,
                    "details": {
                        "activity_id": activity_id,
                        "distance_km": distance_km,
                        "duration_seconds": duration_seconds,
                        "duration_formatted": format_duration(duration_seconds),
                        "average_hr": avg_hr,
                        "max_hr": max_hr,
                        "calories": calories,
                        # --- Add NEW raw daily context to details ---
                        "daily_context": daily_context,
                        # ------------------------------------------
                    },
                    "url": f"https://connect.garmin.com/modern/activity/{activity_id}" if activity_id else None
                }
                activities.append(activity_entry)
                print(f"  [Garmin Source] Added activity: {summary}")

    except GarminConnectAuthenticationError:
        print(f"[Garmin Source] Error: Authentication failed for user {username}. Check credentials.", file=sys.stderr)
    except GarminConnectConnectionError as e:
        print(f"[Garmin Source] Error: Connection error: {e}", file=sys.stderr)
    except GarminConnectTooManyRequestsError:
        print("[Garmin Source] Error: Too many requests. Garmin Connect may be rate-limiting.", file=sys.stderr)
    except Exception as e:
        print(f"[Garmin Source] An unexpected error occurred during processing: {e}", file=sys.stderr)
        # Consider re-raising or logging traceback for debugging
    finally:
        # Ensure logout is called if client was initialized
        if client:
             try:
                 client.logout()
                 print("[Garmin Source] Logout successful.")
             except Exception as e:
                 print(f"[Garmin Source] Error during logout: {e}", file=sys.stderr)

    print(f"[Garmin Source] Finished processing. Returning {len(activities)} activities.")
    return activities

if __name__ == '__main__':
    print("Testing Garmin Source module...")
    # --- Requires environment variables for testing --- 
    # import os
    # from dotenv import load_dotenv
    # load_dotenv()
    # test_user = os.environ.get("GARMIN_USERNAME")
    # test_pass = os.environ.get("GARMIN_PASSWORD")
    # # Updated test format to include new placeholders
    # test_format = "- Did a {distance:.1f} km {activity_type} ({duration_formatted}, Avg HR: {avg_hr}). Steps: {daily_steps}, Sleep: {sleep_duration_formatted} ({deep_sleep_percent}% deep), Stress: {stress_qualifier}.\"
    # if test_user and test_pass:
    #     results = get_activity(test_user, test_pass, test_format)
    #     print(f"\nRetrieved {len(results)} activities:")
    #     for act in results:
    #         print(f"  - {act['summary']} ({act['timestamp']})")
    # else:
    #     print("Skipping test: Set GARMIN_USERNAME and GARMIN_PASSWORD in .env file")
    print("Please run the main script or provide credentials via environment variables for testing.") 