# sunlab-scheduler

:calendar: Weekly shift scheduler for the Brown University CS Department's [Sunlab Consultants](https://cs.brown.edu/degrees/undergrad/jobs/consult/).

The scheduler uses **linear programming** (via the `PuLP` library) to solve for an optimal schedule, taking into account...
- **Employee preferences:** Weekly availability; desired hours per week; preference levels for different shifts
- **Scheduling policies:** Min/max hours per week; max hours per day
- **Department-enforced rules:** Weekly lab opening hours
- ...and more soon!

---

*Built with :sunny: by Alex Mazansky, 2025*
