import pandas as pd
from pulp import value  # type: ignore
from pulp.constants import LpStatus, LpStatusOptimal  # type: ignore

from lp import (
    PREF_NEUTRAL,
    PREF_NOT_PREFERABLE,
    PREF_PREFERABLE,
    PREF_UNAVAILABLE,
    create_schedule,
)
from read_csv import parse_availability


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
    status, x = create_schedule(df_avail)

    if status == LpStatusOptimal:
        print("\n=== SCHEDULE CREATED SUCCESSFULLY ===")
        print_formatted_schedule(x, df_avail)
    else:
        print("\n=== COULD NOT CREATE SCHEDULE ===")
        print(f"Linear Program Status: {LpStatus[status]}")

    return x


def print_formatted_schedule(x: dict, df: pd.DataFrame):
    # print schedule
    for t in df.index:
        for c in df.columns:
            if (c, t) in x and value(x[c, t]) == 1:
                print(f"{t:%a %H:%M}: {c} ({df.loc[t, c]})")
                # TODO: print preference level as a string instead of name
                # TODO: also print how many other ppl are available during each block


if __name__ == "__main__":
    # TODO: use fire
    # TODO: add step where user can manually correct shift preferences

    run("example/availability.csv")
