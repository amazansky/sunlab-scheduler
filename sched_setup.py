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
# PREF_UNAVAILABLE = -1
# PREF_PREFERABLE = 0
# PREF_NEUTRAL = 1
# PREF_NOT_PREFERABLE = 2


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


def _generate_time_blocks(hours: dict[int, tuple[str, str]]) -> list[datetime]:
    # make list iteratively by day
    time_blocks = []

    for day_of_week, (open_time_str, close_time_str) in hours.items():
        # gets the date of the `day_of_week` this week, e.g. the date of the Monday this week if
        # day_of_week == 0
        day_this_week_date = _get_date_for_day_of_current_week(day_of_week)

        # parse lab opening, closing times into datetimes for the current week
        open_datetime, close_datetime = (
            datetime.combine(
                day_this_week_date, datetime.strptime(time_str, "%H:%M").time()
            )
            for time_str in (open_time_str, close_time_str)
        )

        if close_datetime < open_datetime:
            # lab closes at midnight - make sure it registers as the next day
            close_datetime += timedelta(days=1)

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
    time_blocks = _generate_time_blocks(hours)
    return pd.DataFrame(index=time_blocks, columns=consultants)


if __name__ == "__main__":
    # example run
    sched_df = setup_consultant_availability_df(
        SUNLAB_HOURS, ["alice", "bob", "charlie"]
    )
    print(sched_df)
