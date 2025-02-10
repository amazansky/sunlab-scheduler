import pandas as pd
from pulp import LpProblem, LpVariable, lpSum, value  # type: ignore
from pulp.constants import LpBinary, LpMinimize  # type: ignore

from sched_setup import (
    PREF_NEUTRAL,
    PREF_NOT_PREFERABLE,
    PREF_PREFERABLE,
    PREF_UNAVAILABLE,
)

# TODO: refactor this (and other preferences) into a class or something for CLI usage
CONSULTANT_MIN_HOURS = 2
CONSULTANT_MAX_HOURS = 10

BLOCK_LENGTH_MINIMUM = 2  # 1 hr = 2 blocks
BLOCK_LENGTH_MAXIMUM = 10  # 5 hr = 10 blocks


def _get_availability(
    df: pd.DataFrame, consultant: str, time_slot: pd.Timestamp
) -> int:
    return df.loc[time_slot, consultant]  # type: ignore


def _get_preference_cost(
    df: pd.DataFrame, consultant: str, time_slot: pd.Timestamp
) -> int:
    status = _get_availability(df, consultant, time_slot)

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

    # 2. minimum/maximum hours per consultant
    for c in consultants:
        num_consultant_hours = lpSum([0.5 * x[c, t] for t in time_slots])
        prob += num_consultant_hours >= CONSULTANT_MIN_HOURS
        prob += num_consultant_hours <= CONSULTANT_MAX_HOURS

    # 3. not available times
    for c in consultants:
        for t in time_slots:
            if _get_availability(df, c, t) == PREF_UNAVAILABLE:
                prob += x[c, t] == 0

    # 4. maximum block length (don't cross midnight per day)
    for c in consultants:
        # group time slots by day
        unique_days = set(t.date() for t in time_slots)

        for day in unique_days:
            # get time slots for this day
            day_slots = [t for t in time_slots if t.date() == day]

            # apply constraint for each starting time slot in the day
            for t_idx in range(len(day_slots) - BLOCK_LENGTH_MAXIMUM):
                t = day_slots[t_idx]

                next_maxlength_time_blocks = [
                    t + pd.Timedelta(30 * n, "min")
                    for n in range(BLOCK_LENGTH_MAXIMUM + 1)
                    if (t + pd.Timedelta(30 * n, "min")).date() == day
                    # ensure we don't cross midnight
                ]

                # only add constraint if we have blocks to consider
                if next_maxlength_time_blocks:
                    prob += lpSum([x[c, t_] for t_ in next_maxlength_time_blocks]) <= 10

    # TODO: other constraints (give those who requested fewer hours priority?)

    status = prob.solve()
    return status, x


if __name__ == "__main__":
    from sched_setup import (
        SUNLAB_HOURS,
        add_consultant_hours_to_df,
        setup_consultant_availability_df,
    )

    df = setup_consultant_availability_df(
        SUNLAB_HOURS, [f"consult{n:02}" for n in range(15)]
    )
    # set all times to "not preferable" instead of "unavailable" so demo can be solved
    df = df.replace(-1, 2)
    add_consultant_hours_to_df(df, "consult01", 0, "09:00", "11:00", PREF_NEUTRAL)
    # print(df)

    status, x = create_schedule(df)

    print(f"{status=}")

    if status == 1:
        consultants = df.columns
        time_slots = df.index

        for t in time_slots:
            for c in consultants:
                if value(x[c, t]) == 1:
                    print(f"{t:%a %H:%M}: {c} ({_get_availability(df, c, t)})")
