import os
import time
from datetime import datetime, timedelta, time as dtime
from urllib.parse import urlencode

import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from dateutil import tz
from streamlit_plotly_events import plotly_events

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def format_hour_12h(hour: int) -> str:
    """Convert 24-hour format to 12-hour format with AM/PM."""
    if hour == 0:
        return "12 AM"
    elif hour < 12:
        return f"{hour} AM"
    elif hour == 12:
        return "12 PM"
    else:
        return f"{hour - 12} PM"

def get_next_datetime_for_weekday(target_weekday_index: int, hour: int, minute: int, tzinfo):
    """
    Return the next datetime (in the future) for the given weekday index (0=Monday)
    at the specified hour/minute, in the given timezone.
    """
    now = datetime.now(tzinfo)
    today_idx = now.weekday()  # 0 = Monday
    days_ahead = (target_weekday_index - today_idx) % 7
    candidate_date = (now + timedelta(days=days_ahead)).date()

    candidate_dt = datetime.combine(candidate_date, dtime(hour=hour, minute=minute))

    # Attach timezone using dateutil-style tzinfo
    if tzinfo is not None and candidate_dt.tzinfo is None:
        candidate_dt = candidate_dt.replace(tzinfo=tzinfo)

    # Ensure it's in the future
    if candidate_dt <= now:
        candidate_dt = candidate_dt + timedelta(days=7)

    return candidate_dt


def get_places_autocomplete(api_key: str, input_text: str):
    """
    Get autocomplete suggestions from Google Places API.
    Returns a list of place descriptions, or empty list on failure.
    """
    if not input_text or len(input_text) < 2:
        return []
    
    endpoint = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    
    params = {
        "input": input_text,
        "key": api_key,
        "types": "geocode",  # Restrict to addresses
    }
    
    try:
        resp = requests.get(endpoint, params=params, timeout=3)
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        status = data.get("status")
        
        # Handle different API response statuses
        if status == "OK":
            predictions = data.get("predictions", [])
            return [pred["description"] for pred in predictions[:5]]  # Return top 5
        elif status == "ZERO_RESULTS":
            return []
        else:
            # Log error status for debugging (but don't show to user)
            # Common issues: "REQUEST_DENIED" (API not enabled), "INVALID_REQUEST", etc.
            return []
    except Exception as e:
        # Silently fail - don't show errors to user
        return []


def address_input_with_autocomplete(label: str, key: str, default_value: str, api_key: str):
    """
    Create a text input with autocomplete suggestions.
    Returns the selected address.
    """
    # Initialize session state for this input
    if f"{key}_input" not in st.session_state:
        st.session_state[f"{key}_input"] = default_value
    if f"{key}_last_query" not in st.session_state:
        st.session_state[f"{key}_last_query"] = ""
    if f"{key}_suggestions" not in st.session_state:
        st.session_state[f"{key}_suggestions"] = []
    if f"{key}_widget_version" not in st.session_state:
        st.session_state[f"{key}_widget_version"] = 0
    
    # Text input - use a versioned key to force reset when suggestion is selected
    widget_version = st.session_state[f"{key}_widget_version"]
    input_key = f"{key}_text_input_v{widget_version}"
    
    # Get the current input value
    previous_input = st.session_state.get(f"{key}_input", default_value)
    
    current_input = st.sidebar.text_input(
        label,
        value=previous_input,
        key=input_key
    )
    
    # Check if input has changed (compare with previous value)
    input_changed = current_input != previous_input
    
    # Update session state
    st.session_state[f"{key}_input"] = current_input
    
    # Get suggestions if input has changed and is long enough
    if input_changed and len(current_input) >= 2:
        # Fetch new suggestions
        suggestions = get_places_autocomplete(api_key, current_input)
        st.session_state[f"{key}_last_query"] = current_input
        st.session_state[f"{key}_suggestions"] = suggestions
    elif len(current_input) < 2:
        # Clear suggestions if input is too short
        st.session_state[f"{key}_suggestions"] = []
        st.session_state[f"{key}_last_query"] = ""
        suggestions = []
    else:
        # If input hasn't changed, use cached suggestions
        suggestions = st.session_state.get(f"{key}_suggestions", [])
    
    # Show suggestions if available
    # Display suggestions when we have them and the input matches the query
    if suggestions and len(current_input) >= 2:
        # Show suggestions if input matches what we queried
        if current_input == st.session_state[f"{key}_last_query"]:
            st.sidebar.caption("💡 Suggestions:")
            for i, suggestion in enumerate(suggestions):
                if st.sidebar.button(suggestion, key=f"{key}_suggestion_{i}", use_container_width=True):
                    # Update the input value and increment widget version to force reset
                    st.session_state[f"{key}_input"] = suggestion
                    st.session_state[f"{key}_last_query"] = suggestion
                    st.session_state[f"{key}_suggestions"] = []
                    st.session_state[f"{key}_widget_version"] += 1
                    st.rerun()
    
    return st.session_state[f"{key}_input"]


def call_distance_matrix(
    api_key: str,
    origin: str,
    destination: str,
    departure_dt,
    mode: str = "driving",
    traffic_model: str = "best_guess"
):
    """
    Call Google Distance Matrix API for a single origin/destination/time.
    Returns travel time in seconds, or None on failure.
    """
    endpoint = "https://maps.googleapis.com/maps/api/distancematrix/json"

    params = {
        "origins": origin,
        "destinations": destination,
        "mode": mode,
        "departure_time": int(departure_dt.timestamp()),  # seconds since epoch
        "traffic_model": traffic_model,
        "key": api_key,
    }

    resp = requests.get(endpoint, params=params)
    if resp.status_code != 200:
        return None

    data = resp.json()
    # Basic sanity checks
    try:
        row = data["rows"][0]
        element = row["elements"][0]
        if element.get("status") != "OK":
            return None
        # Prefer duration_in_traffic if available
        if "duration_in_traffic" in element:
            return element["duration_in_traffic"]["value"]  # seconds
        else:
            return element["duration"]["value"]  # seconds
    except (KeyError, IndexError):
        return None


def build_traffic_matrix(
    api_key: str,
    origin: str,
    destination: str,
    tz_name: str,
    selected_days: list,
    time_slots: list,
    mode: str,
    traffic_model: str,
    pause_seconds: float,
    progress_bar=None,
    status_text=None
):
    """
    Build a DataFrame indexed by day (rows) and time-of-day (columns),
    with values = travel time in minutes.
    """
    tzinfo = tz.gettz(tz_name)
    records = []
    
    total_calls = len(selected_days) * len(time_slots)
    completed_calls = 0

    for day in selected_days:
        day_idx = DAYS_ORDER.index(day)
        for label, (hour, minute) in time_slots:
            dt_future = get_next_datetime_for_weekday(day_idx, hour, minute, tzinfo)
            travel_seconds = call_distance_matrix(
                api_key=api_key,
                origin=origin,
                destination=destination,
                departure_dt=dt_future,
                mode=mode,
                traffic_model=traffic_model,
            )
            # Be nice to the API
            time.sleep(pause_seconds)

            if travel_seconds is not None:
                travel_minutes = travel_seconds / 60.0
            else:
                travel_minutes = None

            records.append(
                {
                    "day": day,
                    "time_slot": label,
                    "travel_minutes": travel_minutes,
                }
            )
            
            # Update progress
            completed_calls += 1
            if progress_bar is not None:
                progress = completed_calls / total_calls
                progress_bar.progress(progress)
            if status_text is not None:
                status_text.text(f"Completed {completed_calls} of {total_calls} API calls ({day} {label})")

    df = pd.DataFrame(records)
    if df.empty:
        return df

    # Pivot: rows = day, columns = time_slot
    heat_df = df.pivot(index="day", columns="time_slot", values="travel_minutes")
    
    # Reorder columns chronologically (time_slots are already in chronological order)
    time_slot_labels = [label for label, _ in time_slots]
    # Only include columns that exist in the DataFrame
    existing_columns = [col for col in time_slot_labels if col in heat_df.columns]
    heat_df = heat_df[existing_columns]
    
    # Sort rows by DAYS_ORDER
    heat_df = heat_df.reindex(DAYS_ORDER).loc[selected_days]
    return heat_df


# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------

st.set_page_config(page_title="Traffic Heatmap Planner", layout="wide")

st.title("🚗 Traffic Heatmap Planner")
st.write(
    "This tool uses the Google Distance Matrix API to estimate typical travel times "
    "for different **days of the week** and **times of day**, then displays the results "
    "as a heatmap."
)

# ---- API Key ----
st.sidebar.header("Google API Settings")

# First, try to get the key from secrets (server-side only)
# Wrap in try/except to handle case where no secrets file exists
try:
    api_key = st.secrets.get("GOOGLE_MAPS_API_KEY", "")
except Exception:
    api_key = ""

# If no secret is set, fall back to user input (for local testing / BYO-key)
if not api_key:
    api_key = st.sidebar.text_input(
        "Google Maps API key",
        value="",
        type="password",
        help="Enter your own Google Maps API key",
    )

if not api_key:
    st.warning("Enter your Google Maps API key in the sidebar to run the analysis.")
    st.stop()

# ---- Route configuration ----
st.sidebar.header("Route Settings")
st.sidebar.caption("💡 Tip: Type an address and press Enter to see suggestions")
origin = address_input_with_autocomplete("Origin", "origin", "San Francisco, CA", api_key)
destination = address_input_with_autocomplete("Destination", "destination", "San Jose, CA", api_key)

# Button to swap origin and destination
if st.sidebar.button("Swap origin/destination"):
    # Use the session_state keys used by address_input_with_autocomplete
    origin_val = st.session_state.get("origin_input", origin)
    dest_val = st.session_state.get("destination_input", destination)

    # Swap the input values
    st.session_state["origin_input"], st.session_state["destination_input"] = (
        dest_val,
        origin_val,
    )
    
    # Increment widget versions to force widgets to reset with new values
    st.session_state["origin_widget_version"] = st.session_state.get("origin_widget_version", 0) + 1
    st.session_state["destination_widget_version"] = st.session_state.get("destination_widget_version", 0) + 1
    
    # Clear suggestions and last queries for both fields
    st.session_state["origin_suggestions"] = []
    st.session_state["origin_last_query"] = ""
    st.session_state["destination_suggestions"] = []
    st.session_state["destination_last_query"] = ""

    # Re-run so the inputs update visually
    st.rerun()

mode = st.sidebar.selectbox("Travel mode", ["driving", "transit", "bicycling", "walking"])
traffic_model = st.sidebar.selectbox(
    "Traffic model (for driving + future times)",
    ["best_guess", "pessimistic", "optimistic"],
    index=0,
)

# ---- Time / day grid settings ----
st.sidebar.header("Grid Settings")

selected_days = st.sidebar.multiselect(
    "Days of week",
    options=DAYS_ORDER,
    default=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
)

# Create hour options with 12-hour format labels
hour_options = list(range(24))
hour_labels = [format_hour_12h(h) for h in hour_options]

start_hour_label = st.sidebar.select_slider(
    "Start hour",
    options=hour_labels,
    value=hour_labels[7]  # Default to 7 AM
)
start_hour = hour_options[hour_labels.index(start_hour_label)]

end_hour_label = st.sidebar.select_slider(
    "End hour",
    options=hour_labels,
    value=hour_labels[19]  # Default to 7 PM
)
end_hour = hour_options[hour_labels.index(end_hour_label)]
step_minutes = st.sidebar.selectbox("Time step (minutes)", [15, 30, 60], index=2)

# Minimal input validation
if end_hour <= start_hour:
    st.sidebar.error("End hour must be after start hour.")
    st.stop()

# Timezone (for departure_time)
tz_name = st.sidebar.text_input("Timezone (IANA name)", value="America/Los_Angeles")

pause_seconds = st.sidebar.slider(
    "Pause between API calls (seconds)",
    min_value=0.0,
    max_value=1.0,
    value=0.1,
    step=0.05,
)

st.sidebar.info(
    "⚠️ Each cell in the heatmap = one API call. A 5-day × 13-hour (1h step) grid "
    "is 65 calls. Keep quotas in mind."
)

# Build time slots
time_slots = []
current_minutes = start_hour * 60
end_minutes = end_hour * 60

while current_minutes <= end_minutes:
    hour = current_minutes // 60
    minute = current_minutes % 60
    # Convert to 12-hour format with AM/PM
    if hour == 0:
        display_hour = 12
        period = "AM"
    elif hour < 12:
        display_hour = hour
        period = "AM"
    elif hour == 12:
        display_hour = 12
        period = "PM"
    else:
        display_hour = hour - 12
        period = "PM"
    label = f"{display_hour}:{minute:02d} {period}"
    time_slots.append((label, (hour, minute)))
    current_minutes += step_minutes

st.write("### Configuration summary")
st.write(f"- **Origin:** {origin}")
st.write(f"- **Destination:** {destination}")
st.write(f"- **Days:** {', '.join(selected_days) if selected_days else 'None selected'}")
st.write(f"- **Time slots:** {len(time_slots)}")
st.write(f"- **Mode:** {mode}, **Traffic model:** {traffic_model}")
st.write(f"- **Timezone:** {tz_name}")

if not selected_days:
    st.warning("Select at least one day of the week to proceed.")
    st.stop()

run_btn = st.button("Build traffic heatmap")

if run_btn:
    total_calls = len(selected_days) * len(time_slots)
    st.write(f"**Querying {total_calls} time slots...**")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    heat_df = build_traffic_matrix(
        api_key=api_key,
        origin=origin,
        destination=destination,
        tz_name=tz_name,
        selected_days=selected_days,
        time_slots=time_slots,
        mode=mode,
        traffic_model=traffic_model,
        pause_seconds=pause_seconds,
        progress_bar=progress_bar,
        status_text=status_text,
    )
    
    progress_bar.empty()
    status_text.empty()

    if heat_df.empty:
        st.error("No data returned from Distance Matrix API. Check inputs or quotas.")
    else:
        st.subheader("Travel time heatmap (minutes)")
        st.dataframe(heat_df.style.format("{:.1f}"))

        # Build the heatmap figure
        fig = px.imshow(
            heat_df,
            labels=dict(x="Time of day", y="Day of week", color="Travel time (min)"),
            aspect="auto",
            origin="upper",
            text_auto=".1f",
            color_continuous_scale="Turbo",
        )
        fig.update_layout(height=600)

        # Use plotly_events for clickable heatmap
        # This should render the chart AND enable click events
        selected_points = plotly_events(
            fig,
            click_event=True,
            hover_event=False,
            select_event=False,
            key="traffic_heatmap_events",
        )

        st.caption(
            "Click any cell to see details below. "
            "Estimates are based on Google's typical/predicted traffic for future "
            "departure times, derived from historical traffic patterns."
        )

        # If user clicked a cell, show details + Google Maps link
        if selected_points:
            point = selected_points[0]
            # For px.imshow with a DataFrame, x = column label, y = index label, z = value
            cell_time_label = point.get("x")
            cell_day = point.get("y")
            cell_minutes = point.get("z")

            st.markdown(
                f"**Selected:** {cell_day} at {cell_time_label} — "
                f"~{cell_minutes:.1f} minutes of travel time"
            )

            # Build a Google Maps directions URL for the current origin/destination/mode
            query_params = {
                "api": 1,
                "origin": origin,
                "destination": destination,
                "travelmode": mode,
            }
            maps_url = "https://www.google.com/maps/dir/?" + urlencode(query_params)

            st.markdown(f"[Open this route in Google Maps]({maps_url})")

        # Allow user to download the heatmap data as CSV
        csv_bytes = heat_df.to_csv().encode("utf-8")
        st.download_button(
            label="Download heatmap data as CSV",
            data=csv_bytes,
            file_name="traffic_heatmap.csv",
            mime="text/csv",
            key="download_heatmap_csv",
        )
else:
    st.info("Set your parameters and click **Build traffic heatmap** to generate the chart.")
