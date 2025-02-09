from datetime import datetime, timedelta
import pandas as pd

SUNLAB_HOURS = {
    # Day: (Open time, Close time)
    "Mon": ("09:00", "00:00"),
    "Tue": ("09:00", "00:00"),
    "Wed": ("09:00", "00:00"),
    "Thu": ("09:00", "00:00"),
    "Fri": ("09:00", "22:00"),
    "Sat": ("12:00", "22:00"),
    "Sun": ("12:00", "00:00"),
}


def _generate_time_blocks(hours: dict[str, tuple[str, str]]) -> list[str]:
    # make list iteratively by day
    time_blocks = []

    for day, (open_time_str, close_time_str) in hours.items():
        # parse opening, closing times
        open_time_parsed = datetime.strptime(open_time_str, "%H:%M")
        close_time_parsed = datetime.strptime(close_time_str, "%H:%M")

        if close_time_parsed < open_time_parsed:
            # lab closes at midnight - make sure it registers as the next day
            close_time_parsed += timedelta(days=1)

        # iterate through half-hour time blocks and add to list
        current_time = open_time_parsed
        while current_time < close_time_parsed:
            next_time = min(current_time + timedelta(minutes=30), close_time_parsed)
            current_block = (day, current_time, next_time)
            time_blocks.append(current_block)

            current_time = next_time

    return time_blocks


def sched_setup_df(
    hours: dict[str, tuple[str, str]], consultants: list[str]
) -> pd.DataFrame:
    pass


if __name__ == "__main__":
    # example run
    # sched_df = sched_setup_df(SUNLAB_HOURS, ["alice", "bob", "charlie"])
    # print(sched_df)

    # print generated time blocks
    print("\n".join(str(tup) for tup in _generate_time_blocks(SUNLAB_HOURS)))
