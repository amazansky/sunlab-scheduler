import pandas as pd
from pulp import value  # type: ignore
from pulp.constants import LpStatus, LpStatusOptimal  # type: ignore

from lp import create_schedule
from read_csv import parse_availability


def run(csv_file: str) -> dict:
    print("\n=== PARSING AVAILABILITY ===")
    df_avail = parse_availability(csv_file)
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


if __name__ == "__main__":
    run("example/availability.csv")
