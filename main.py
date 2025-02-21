import pandas as pd
from pulp.constants import LpStatus, LpStatusOptimal  # type: ignore

from lp import (
    PREF_NEUTRAL,
    PREF_NOT_PREFERABLE,
    PREF_PREFERABLE,
    PREF_UNAVAILABLE,
    create_schedule,
)
from read_csv import allocate_feasible_blocks, parse_availability
from sched_format import ScheduleFormatter


def _print_consultant_requests(csv_file: str):
    df = pd.read_csv(csv_file)

    # TODO: don't hardcode
    email_colname = df.columns[1]
    request_colname = df.columns[-1]

    # get rows where consultants have made special requests
    has_requests = ~df.loc[:, request_colname].isna()

    df2 = df.loc[has_requests, [email_colname, request_colname]]

    for _, (email, request) in df2.iterrows():
        print(f"{email}\n{request}\n")


def run(csv_file: str) -> dict:
    print("\n=== PARSING AVAILABILITY ===")
    df_avail = parse_availability(csv_file)
    print(df_avail)

    # get possible number of hours to assign to each consultant in preparation for LP
    # TODO: refactor this to a different place probably
    feasible_hours = allocate_feasible_blocks(csv_file)

    # output to file to give the user a chance to change preference levels as per consultant
    # requests. (really should come up with a better way of doing this)
    tmp_filename = "tmp_avail.csv"
    print(
        f"\nNow outputting to {tmp_filename}... "
        + "Please make any preference level edits now.\nKey:"
        + f"\n {PREF_PREFERABLE}: PREFERRED"
        + f"\n {PREF_NEUTRAL}: NEUTRAL"
        + f"\n {PREF_NOT_PREFERABLE}: NOT PREFERRED"
        + f"\n {PREF_UNAVAILABLE}: UNAVAILABLE"
        + "\n\nConsultant requests:"
    )
    _print_consultant_requests(csv_file)
    df_avail.to_csv("tmp_avail.csv")

    # wait until user is done and presses return;
    input("\nPress return when finished...\n>")

    # use index_col to make sure the DatetimeIndex gets preserved
    # TODO: come up with a better way of doing this
    df_avail = pd.read_csv("tmp_avail.csv", index_col=0, parse_dates=True)

    print("New df:")  # TODO: maybe instead print a diff of the two dfs?
    print(df_avail)

    print("\n=== CREATING SCHEDULE ===")
    status, x = create_schedule(df_avail, feasible_hours)

    if status == LpStatusOptimal:
        print("\n=== SCHEDULE CREATED SUCCESSFULLY ===")
        sched_formatter = ScheduleFormatter(x, df_avail)
        print("=====")
        sched_formatter.print_schedule_by_day()
        print("=====")
        sched_formatter.print_schedule_by_consultant()
    else:
        print("\n=== COULD NOT CREATE SCHEDULE ===")
        print(f"Linear Program Status: {LpStatus[status]}")

    return x


if __name__ == "__main__":
    # TODO: use fire
    # TODO: add step where user can manually correct shift preferences

    run("example/availability.csv")
