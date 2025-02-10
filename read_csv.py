import re

import pandas as pd

from sched_setup import (
    PREF_NEUTRAL,
    SUNLAB_HOURS,
    add_consultant_hours_to_df,
    setup_consultant_availability_df,
)


def convert_to_24h_format(time_str):
    """
    Converts time strings like '9am-2pm' to ('09:00', '14:00') format.
    """
    match = re.match(
        r"(\d{1,2})(?::(\d{2}))?([ap]m?)? ?- ?(\d{1,2})(?::(\d{2}))?([ap]m)?",
        time_str.strip().lower(),
    )
    if not match:
        return None

    start_hour, start_minute, start_period, end_hour, end_minute, end_period = (
        match.groups()
    )

    start_hour = int(start_hour)
    start_minute = start_minute if start_minute else "00"
    end_hour = int(end_hour)
    end_minute = end_minute if end_minute else "00"

    if start_period == "pm" and start_hour != 12:
        start_hour += 12
    elif start_period == "am" and start_hour == 12:
        start_hour = 0

    if end_period == "pm" and end_hour != 12:
        end_hour += 12
    elif end_period == "am" and end_hour == 12:
        end_hour = 0

    return f"{start_hour:02}:{start_minute}", f"{end_hour:02}:{end_minute}"


def parse_availability(csv_file, sunlab_hours):
    """
    Parses consultant availability from a CSV file and returns a DataFrame.
    """
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None

    # extract consultant emails
    if "Email Address" not in df.columns:
        print("Error: 'Email Address' column not found in CSV.")
        return None
    consultants = df["Email Address"].dropna().unique().tolist()

    # initialize availability df
    availability_df = setup_consultant_availability_df(sunlab_hours, consultants)

    # map csv column names to weekdays
    # TODO: do something clever with strptime/strftime here
    days = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    for _, row in df.iterrows():
        email = row.get("Email Address")
        if pd.isna(email):
            continue

        for day, day_index in days.items():
            raw_times = row.get(day, "None")

            if (
                pd.isna(raw_times)
                or raw_times.lower() == "none"
                or raw_times.lower() == "na"
            ):
                continue

            for slot in raw_times.split(","):
                slot = slot.strip()
                parsed_time = convert_to_24h_format(slot)

                if parsed_time:  # parse succeeded
                    start_time, end_time = parsed_time

                else:  # parse failed - get manual input
                    user_input = input(
                        f"Cannot parse time slot '{slot}' for {email} on {day}. "
                        + 'Please enter in "HH:MM-HH:MM" format or "None": '
                    )
                    if user_input.strip().lower() == "none":
                        continue

                    start_time, end_time = user_input.strip().split("-")

                # TODO: maybe account for adding preference levels during this stage?
                # for now just do manually
                add_consultant_hours_to_df(
                    availability_df,
                    email,
                    day_index,
                    start_time,
                    end_time,
                    PREF_NEUTRAL,
                )

    return availability_df


if __name__ == "__main__":
    # example usage
    csv_file_path = "example/availability.csv"

    availability_df = parse_availability(csv_file_path, SUNLAB_HOURS)
    print(availability_df)
