from typing import Optional

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

DAILY_MAX_BLOCKS = 10  # 5 hr = 10 blocks

# TODO: refactor this into preference enum?
PREFERENCE_COSTS = {
    PREF_PREFERABLE: 0,
    PREF_NEUTRAL: 1,
    PREF_NOT_PREFERABLE: 4,
    PREF_UNAVAILABLE: 100,
}

SHIFT_CHANGE_PENALTY = 6


def create_schedule(
    df: pd.DataFrame, feasible_blocks: Optional[dict[str, tuple[int, int]]] = None
) -> tuple[int, dict]:
    """
    Creates schedule based on consultant availability df generated in sched_setup.py and feasible
    block allocations generated in read_csv.py
    """
    prob = LpProblem("consultant_scheduling", LpMinimize)

    consultants = df.columns
    time_slots = df.index

    # precompute availability and days to reduce function calls
    availability = {(c, t): df.loc[t, c] for c in consultants for t in time_slots}

    days = df.index.map(lambda t: t.date()).unique()
    day_slots = {day: df.index[df.index.map(lambda t: t.date()) == day] for day in days}

    # only create decision variables where consultants are available
    x = {
        (c, t): LpVariable(f"shift_{c}_{t}", cat=LpBinary)
        for (c, t), avail in availability.items()
        if avail != PREF_UNAVAILABLE
    }

    # reduce number of shift changes
    # TODO: make this daily instead of across whole schedule
    y = {
        (c, t): LpVariable(f"shift_change_{c}_{t}", cat=LpBinary)
        for (c, t) in x.keys()
        if t != time_slots[-1]
    }

    # objective function
    preference_cost = lpSum(
        x[c, t] * PREFERENCE_COSTS[availability[c, t]] for c, t in x.keys()
    )

    # constraints
    # 0. penalize shift changes within same day
    for c in consultants:
        for _, slots in day_slots.items():  # slots within each day
            for i in range(len(slots) - 1):
                t, t_next = slots[i], slots[i + 1]
                if (c, t) in x and (c, t_next) in x:
                    prob += y[c, t] >= x[c, t] - x[c, t_next]
                    prob += y[c, t] >= x[c, t_next] - x[c, t]

    shift_changes = lpSum(y.values())

    prob += preference_cost + SHIFT_CHANGE_PENALTY * shift_changes

    # constraints
    # 1. one consultant per time slot
    for t in time_slots:
        prob += lpSum(x[c, t] for c in consultants if (c, t) in x) == 1

    # 2. minimum/maximum weekly hours per consultant
    # print(f"{feasible_blocks=}")
    for c in consultants:
        total_blocks = lpSum(x[c, t] for t in time_slots if (c, t) in x)

        if feasible_blocks is None:
            # specific hours not specified: just use generic 2-10 range
            prob += total_blocks >= CONSULTANT_MIN_HOURS * 2  # convert hours to blocks
            prob += total_blocks <= CONSULTANT_MAX_HOURS * 2  # convert hours to blocks

        else:
            # specific hours were specified in the dict - use 80-100% of the # of blocks requested
            # (already know the hours request is bounded by 2-10 range from the allocate function)
            consultant_blocks_min, consultant_blocks_max = feasible_blocks[c]

            print(f"{c=}, {consultant_blocks_max=}, {consultant_blocks_min=}")

            prob += total_blocks >= consultant_blocks_min
            prob += total_blocks <= consultant_blocks_max

    # 3. maximum 5 hours (10 blocks) per day per consultant
    for c in consultants:
        for day in days:
            slots = day_slots[day]
            prob += lpSum(x[c, t] for t in slots if (c, t) in x) <= DAILY_MAX_BLOCKS

    # status = prob.solve(PULP_CBC_CMD(msg=True, gapRel=0.02))
    status = prob.solve()
    return status, x


if __name__ == "__main__":
    from sched_setup import (
        SUNLAB_HOURS,
        add_consultant_hours_to_df,
        setup_consultant_availability_df,
    )

    mock_consultants = [f"consult{n:02}" for n in range(15)]
    df = setup_consultant_availability_df(SUNLAB_HOURS, mock_consultants)

    # add mock consultant availability
    for cn in range(len(mock_consultants)):
        add_consultant_hours_to_df(
            df, mock_consultants[cn], cn % 7, "09:00", "00:00", PREF_NEUTRAL
        )
        add_consultant_hours_to_df(
            df, mock_consultants[cn], cn + 1 % 7, "09:00", "14:00", PREF_PREFERABLE
        )

    status, x = create_schedule(df)

    print(f"{status=}")

    # print schedule
    if status == 1:
        for t in df.index:
            for c in df.columns:
                if (c, t) in x and value(x[c, t]) == 1:
                    print(f"{t:%a %H:%M}: {c} ({df.loc[t, c]})")
