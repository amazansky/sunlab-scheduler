from datetime import date, datetime, timedelta

import pandas as pd

SUNLAB_HOURS = {
    # TODO: make the days of the week into an enum
    # Day: (Open time, Close time)
    0: ("09:00", "00:00"),  # Monday
    1: ("09:00", "00:00"),  # Tuesday
    2: ("09:00", "00:00"),  # Wednesday
    3: ("09:00", "00:00"),  # Thursday
    4: ("09:00", "22:00"),  # Friday
    5: ("12:00", "22:00"),  # Saturday
    6: ("12:00", "00:00"),  # Sunday
}

# TODO: make this into an enum
PREF_UNAVAILABLE = 0
PREF_NOT_PREFERABLE = 1
PREF_NEUTRAL = 2
PREF_PREFERABLE = 3


def _get_date_for_day_of_current_week(day_of_week: int) -> date:
    """
    Gets the date of this week's `day_of_week`
    This is so that we can use actual datetime objects in the schedule and select them using pandas
    indexing.

    E.g. if today is Thursday, February 23rd (Thursday == 3), then _get_dow_date(1) would return
    Tuesday, February 21st (Tuesday == 1).
    """
    today = date.today()
    most_recent_monday = today - timedelta(days=today.weekday())

    return most_recent_monday + timedelta(days=day_of_week)


def _get_range_start_end_datetimes(
    day_of_week: int, start_time: str, end_time: str
) -> tuple[datetime, datetime]:
    """
    Given start and end times as strings on a given day of the week, generates the
    corresponding datetimes on the specified day of the current week.
    """
    day_this_week_date = _get_date_for_day_of_current_week(day_of_week)

    start_datetime, end_datetime = (
        datetime.combine(
            day_this_week_date, datetime.strptime(time_str, "%H:%M").time()
        )
        for time_str in (start_time, end_time)
    )

    if end_datetime < start_datetime:
        # lab closes at midnight - make sure it registers as the next day
        end_datetime += timedelta(days=1)

    return start_datetime, end_datetime


def _generate_time_blocks(hours: dict[int, tuple[str, str]]) -> list[datetime]:
    """
    Generates a list of datetimes in half-hour increments for each day of the week according to that
    day's lab opening hours.
    """
    # make list iteratively by day
    time_blocks = []

    for day_of_week, (open_time_str, close_time_str) in hours.items():
        # parse lab opening, closing times into datetimes for the current week
        open_datetime, close_datetime = _get_range_start_end_datetimes(
            day_of_week, open_time_str, close_time_str
        )

        # get all half-hour blocks between open and close datetimes
        seconds_diff = (close_datetime - open_datetime).total_seconds()
        minutes_diff = seconds_diff / 60
        num_blocks = int(minutes_diff / 30)  # integer division should be ok here

        time_blocks += [
            open_datetime + timedelta(minutes=30 * n) for n in range(num_blocks)
        ]

    return time_blocks


def setup_consultant_availability_df(
    hours: dict[int, tuple[str, str]], consultants: list[str]
) -> pd.DataFrame:
    """
    Sets up the consultant availability df using the lab's opening hours and a list of consultants.
    """
    time_blocks = _generate_time_blocks(hours)
    df = pd.DataFrame(index=time_blocks, columns=consultants)

    df_filled = df.fillna(PREF_UNAVAILABLE)  # use -1 (not available) as default value
    return df_filled


def add_consultant_hours_to_df(
    df: pd.DataFrame,
    consultant: str,
    day_of_week: int,
    start_time: str,
    end_time: str,
    pref_level: int,
):
    """
    Modifies df inplace to add availability for the specified consultant between the specified
    start and end times on the given day of the week.
    """
    start_datetime, end_datetime = _get_range_start_end_datetimes(
        day_of_week, start_time, end_time
    )

    # make end time exclusive so that (start_time="09:00", end_time="10:00") only selects 9am and
    # 9:30am blocks
    end_datetime -= timedelta(microseconds=1)

    df.loc[start_datetime:end_datetime, consultant] = pref_level  # type: ignore


if __name__ == "__main__":
    # example run
    sched_df = setup_consultant_availability_df(
        SUNLAB_HOURS, ["alice", "bob", "charlie"]
    )
    add_consultant_hours_to_df(sched_df, "alice", 0, "09:00", "10:00", PREF_PREFERABLE)
    print(sched_df)
