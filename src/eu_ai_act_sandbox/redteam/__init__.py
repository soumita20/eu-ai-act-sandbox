"""Bounded, fixture-driven adversarial checks for registered first-party apps."""

from .runner import RedTeamCaseResult, RedTeamRun, run_red_team

__all__ = ["RedTeamCaseResult", "RedTeamRun", "run_red_team"]
