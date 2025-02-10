import pandas as pd
from pulp import LpProblem, LpVariable, lpSum, value  # type: ignore
from pulp.constants import LpBinary, LpMinimize  # type: ignore

from sched_setup import PREF_NEUTRAL, PREF_NOT_PREFERABLE, PREF_PREFERABLE


def _get_preference_cost(df: pd.DataFrame, consultant: str, time_slot: pd.Timestamp):
    status = df.loc[time_slot, consultant]  # type: ignore

    # TODO: refactor to use enum
    if status == PREF_PREFERABLE:
        return 0
    elif status == PREF_NEUTRAL:
        return 1
    elif status == PREF_NOT_PREFERABLE:
        return 4
    else:  # status == PREF_UNAVAILABLE
        return 100


def create_schedule(df: pd.DataFrame):
    """
    Creates schedule based on consultant availability df generated in sched_setup.py
    """
    prob = LpProblem("consultant_scheduling", LpMinimize)

    consultants = df.columns
    time_slots = df.index

    # decision variables
    x = LpVariable.dicts(
        "shift",
        ((c, t) for c in consultants for t in time_slots),
        cat=LpBinary,
    )

    # TODO: add shift change constraints
    # y = LpVariable.dicts(
    #     "shift_change",
    #     ((c, t) for c in consultants for t in time_slots[:-1]),
    #     cat=LpBinary,
    # )

    # objective function
    preference_cost = lpSum(
        [
            x[c, t] * _get_preference_cost(df, c, t)
            for c in consultants
            for t in time_slots
        ]
    )

    prob += preference_cost  # TODO: + 100 * shift_changes

    # constraints
    # 1. one consultant per time slot
    for t in time_slots:
        prob += lpSum([x[c, t] for c in consultants]) == 1

    # TODO: add other constraints

    status = prob.solve()
    return status, x


if __name__ == "__main__":
    from sched_setup import (
        SUNLAB_HOURS,
        add_consultant_hours_to_df,
        setup_consultant_availability_df,
    )

    df = setup_consultant_availability_df(SUNLAB_HOURS, ["alice", "bob", "charlie"])
    add_consultant_hours_to_df(df, "alice", 0, "09:00", "11:00", PREF_NEUTRAL)

    status, x = create_schedule(df)

    consultants = df.columns
    time_slots = df.index

    for t in time_slots:
        for c in consultants:
            if value(x[c, t]) == 1:
                print(f"{t:%a %H:%M}: {c}")
