"""Module for fetching Garmin Connect activity using garminconnect library."""

import sys
import logging
from datetime import datetime, timedelta, timezone

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

def get_activity(username: str | None, password: str | None, activity_format: str) -> list[Activity]:
    """
    Fetches recent Garmin activities (last 24 hours) using the garminconnect library.
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
        print(f"[Garmin Source] Fetching activities from {start_date} to {end_date}...")

        # Fetch activities (adjust limit as needed)
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
                        # --- Add new metrics to format_data --- 
                        'avg_hr': avg_hr if avg_hr is not None else "N/A",
                        'max_hr': max_hr if max_hr is not None else "N/A",
                        'calories': int(calories) if calories is not None else "N/A", # Convert calories to int if possible
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
                        # --- Add raw metrics to details --- 
                        "average_hr": avg_hr,
                        "max_hr": max_hr,
                        "calories": calories,
                        # ----------------------------------
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
    # test_format = "- Did a {distance:.1f} km {activity_type} workout."
    # if test_user and test_pass:
    #     results = get_activity(test_user, test_pass, test_format)
    #     print(f"\nRetrieved {len(results)} activities:")
    #     for act in results:
    #         print(f"  - {act['summary']} ({act['timestamp']})")
    # else:
    #     print("Skipping test: Set GARMIN_USERNAME and GARMIN_PASSWORD in .env file")
    print("Please run the main script or provide credentials via environment variables for testing.") 