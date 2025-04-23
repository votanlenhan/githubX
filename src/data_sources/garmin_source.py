"""Placeholder module for fetching Garmin Connect activity."""

import sys
from datetime import datetime, timedelta, timezone

# Define the standard Activity structure (can be imported from a common module later)
Activity = dict[str, any]

def get_activity(username: str | None, password: str | None, activity_format: str) -> list[Activity]:
    """
    Placeholder function to fetch Garmin activity.
    Currently returns an empty list.
    Actual implementation using garminconnect or similar needed here.
    """
    print("[Garmin Source] Placeholder function called. Garmin integration not yet implemented.")
    
    if not username or not password:
         print("[Garmin Source] Warning: Username or password not provided.", file=sys.stderr)
         # In a real scenario, you'd try to login here
         return []

    # --- TODO: Implement actual Garmin Connect login and data fetching ---
    # Example using a library (pseudo-code):
    # try:
    #     client = Garmin(username, password)
    #     client.login()
    #     activities_data = client.get_activities_by_date(
    #         datetime.now(timezone.utc).date() - timedelta(days=1), # Yesterday
    #         datetime.now(timezone.utc).date() # Today start
    #     )
    #     # Process activities_data into the standard Activity list format...
    #     # Handle pagination if needed
    # except Exception as e:
    #      print(f"[Garmin Source] Error fetching activity: {e}", file=sys.stderr)
    #      return [] # Return empty list on error

    # For now, just return empty
    activities: list[Activity] = []
    return activities

if __name__ == '__main__':
    print("Testing Garmin Source module (Placeholder)...")
    # Test call requires credentials, skipping for placeholder
    print("Actual implementation needed for testing.") 