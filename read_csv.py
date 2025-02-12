import re
from math import ceil

import pandas as pd

from lp import CONSULTANT_MAX_HOURS, CONSULTANT_MIN_HOURS
from sched_setup import (
    PREF_NEUTRAL,
    SUNLAB_HOURS,
    add_consultant_hours_to_df,
    setup_consultant_availability_df,
)

TOT_WEEKLY_SUNLAB_HOURS = 95


def _convert_to_24h_format(time_str: str) -> tuple[str, str] | None:
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


def _hours_to_blocks(hours: int):
    # TODO: use this more
    return hours * 2


def allocate_feasible_blocks(
    csv_file: str, total_hours: int = TOT_WEEKLY_SUNLAB_HOURS
) -> dict[str, tuple[int, int]]:
    """
    Allocates feasible blocks to consultants based on their requested hours.

    If a consultant has requested fewer than the possible number of weekly hours per consultant,
    they get their request. Any consultants who have requested more than what is possible get the
    average of however many hours remain.

    Returns dict in form {"consultant_email@brown.edu": (min_blocks), (max_blocks)}
    (note: 2 blocks per hour)
    """
    df = pd.read_csv(csv_file)

    # TODO: don't hardcode column indices - maybe rename columns or set standard?
    requested_blocks = df.iloc[:, 1:3].dropna()
    # convert hours to blocks
    requested_blocks.iloc[:, 1] = requested_blocks.iloc[:, 1].astype(int) * 2

    allocation = {}
    remaining_blocks = _hours_to_blocks(total_hours)
    remaining_consultants = len(requested_blocks)

    while remaining_consultants > 0:
        avg_blocks = remaining_blocks / remaining_consultants
        reassess = []

        for _, (email, blocks) in requested_blocks.iterrows():
            if (blocks < _hours_to_blocks(CONSULTANT_MIN_HOURS)) or (
                blocks > _hours_to_blocks(CONSULTANT_MAX_HOURS)
            ):
                raise RuntimeError(
                    f"consultant {email} requested illegal number of hours: {blocks / 2} "
                    + f"(min: {CONSULTANT_MIN_HOURS}, max: {CONSULTANT_MAX_HOURS})"
                )

            if blocks < avg_blocks:
                # make sure they get exactly their request if they requested less than average
                allocation[email] = (blocks, blocks)
                remaining_blocks -= blocks
                remaining_consultants -= 1
            else:
                reassess.append((email, blocks))

        if len(reassess) == remaining_consultants:
            break

    if len(reassess) == 0:
        # TODO: remove this later if i want to add flexibility to leave some hours empty
        raise RuntimeError("Warning: Unallocated hours remaining.")

    # need to allocate blocks to everyone who requested over average
    avg_blocks = remaining_blocks / remaining_consultants

    max_default_allocation = ceil(1.05 * avg_blocks)

    # TODO: add some sort of validation to make sure this doesn't leave the people who requested
    # more hours with less than the ones who requested fewer
    min_default_allocation = ceil(0.85 * avg_blocks)

    for email, _ in reassess:
        allocation[email] = (min_default_allocation, max_default_allocation)

    print("HOURS ALLOCATION:")
    alloc_str = [
        f"{email}: {min/2:.1f}-{max/2:.1f} hrs ({min}-{max} blocks)"
        for email, (min, max) in allocation.items()
    ]
    print("\n".join(alloc_str))

    return allocation


def parse_availability(csv_file: str) -> pd.DataFrame:
    """
    Parses consultant availability from a CSV file and returns a DataFrame.
    """
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        raise RuntimeError(f"Error reading CSV file: {e}") from e

    # extract consultant emails
    if "Email Address" not in df.columns:
        raise RuntimeError("Error: 'Email Address' column not found in CSV.")

    consultants = df["Email Address"].dropna().unique().tolist()

    # initialize availability df
    availability_df = setup_consultant_availability_df(SUNLAB_HOURS, consultants)  # type: ignore

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
                parsed_time = _convert_to_24h_format(slot)

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
    csv_file_path = "Consultant weekly shift scheduling Spring 2025 (Responses) - Form Responses 1(2).csv"

    # availability_df = parse_availability(csv_file_path)
    # print(availability_df)

    from pprint import pprint

    pprint(allocate_feasible_blocks(csv_file_path))
