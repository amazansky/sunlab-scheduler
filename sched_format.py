import pandas as pd
from pulp import value  # type: ignore

# name of column that gets added to consultant availability df
CONSULTANT_COLNAME = "consultant"


class ScheduleFormatter:
    """
    Takes raw schedule output from create_schedule() and prints formatted output
    """

    def __init__(
        self,
        assignments: dict,
        consultant_availability: pd.DataFrame,
    ):
        """
        Initialize new schedule formatter

        assignments: dict output from create_schedule()
        consultant_availability: modified dataframe output from parse_availability()
        """
        self.assignments = assignments
        self.df_orig = consultant_availability.copy()

        # transformation pipeline. after completion, self.shifts is a df containing the consolidated
        # shifts for all consultants
        self.df_shifts = self.df_orig.copy()
        self._fill_consultant_assignments()
        self._consolidate_shifts()

    def _fill_consultant_assignments(self):
        """
        Fills a DataFrame with consultant assignments from an assignments dictionary (the output
        from create_schedule)

        df: DataFrame with datetime index
        assignments: Dictionary of (consultant, time) tuples

        Sets self.df_shifts to the resulting DataFrame with new 'consultant' column containing
        active consultant names
        """
        self.df_shifts[CONSULTANT_COLNAME] = None

        # Fill in assignments
        for consultant, time in self.assignments:
            if value(self.assignments[consultant, time]) == 1:
                self.df_shifts.loc[time, CONSULTANT_COLNAME] = consultant

    def _consolidate_shifts(self):
        """
        Consolidates consecutive 30-minute blocks into single shifts.

        df: DataFrame with datetime index and consultant column
        """
        df = self.df_shifts.copy()

        # Mark where consultant changes or there's a time gap
        df["new_shift"] = (
            # Consultant changed
            (df[CONSULTANT_COLNAME] != df[CONSULTANT_COLNAME].shift())
            |
            # Time gap (more than 30 min)
            (df.index.to_series().diff() > pd.Timedelta(minutes=30))
        )

        # Create group numbers for each shift
        df["shift_group"] = df["new_shift"].cumsum()

        # group by shift and aggregate
        shifts = df.groupby("shift_group")[CONSULTANT_COLNAME].first().to_frame()

        # add start and end times from the index
        shifts["start"] = df.groupby("shift_group").apply(lambda x: x.index[0])  # type: ignore
        shifts["end"] = df.groupby("shift_group").apply(lambda x: x.index[-1])  # type: ignore

        # add 30 minutes to end time (since each block represents the start time)
        shifts["end"] = shifts["end"] + pd.Timedelta(minutes=30)

        # sort by start time
        shifts = shifts.sort_values("start")

        # set back to class df field
        self.df_shifts = shifts

    def print_schedule_by_day(self):
        """Print schedule grouped by day"""
        current_day = None

        for _, row in self.df_shifts.iterrows():
            day = f"{row['start']:%A}"
            if day != current_day:
                print(f"\n{day}:")
                current_day = day

            start_time = f"{row['start']:%H:%M}"
            end_time = f"{row['end']:%H:%M}"
            print(f"{start_time}-{end_time} {row[CONSULTANT_COLNAME]}")

    def print_schedule_by_consultant(self):
        """Print schedule grouped by consultant"""

        # helper function
        def format_time(time):
            "Human readable time"
            verbose_str = f"{time:%I:%M%p}"
            clean_str = verbose_str.lstrip("0").replace(":00", "").lower()

            return clean_str

        # Group shifts by consultant
        consultant_groups = self.df_shifts.groupby(CONSULTANT_COLNAME)

        for consultant, consultant_shifts in consultant_groups:
            print(f"\n*{consultant}:*")

            # Sort shifts by start time
            for _, shift in consultant_shifts.sort_values("start").iterrows():
                day = f"{shift['start']:%a}"
                start_time = format_time(shift["start"])
                end_time = format_time(shift["end"])
                print(f"{day} {start_time}-{end_time}")
