"""Shared timing and safety limits used by desktop workflows.

The action timeout leaves room for a final capture inside the 30-second
watchdog. Longer policies use deadlines and stop-aware slices; the shorter
Daily retry limits do not override proven natural training or gather queues.
"""

AUTOMATION_STEP_TIMEOUT_SECONDS = 24.0

DAILY_TOWN_RENDER_PASSIVE_CAP_SECONDS = 29.0

DAILY_PROFILE_RETURN_PASSIVE_CAP_SECONDS = 16.0

MAX_SINGLE_WAIT_SECONDS = 0.2

DAILY_RETRY_LOCK_MAX_SECONDS = 10.0

DAILY_DONATION_TASK_TARGET = 40

DAILY_DONATION_WINDOW_CAP = 25

DAILY_DONATION_WINDOW_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS

DAILY_DONATION_UNAVAILABLE_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS

DAILY_HERO_FREE_RECRUIT_RETRY_SECONDS = 5 * 60

DAILY_WAREHOUSE_SUPPLY_RETRY_SECONDS = 3 * 60

DAILY_WAREHOUSE_SUPPLY_FAILURE_RETRY_SECONDS = 10

DAILY_IDLE_FALLBACK_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS

DAILY_IDLE_STATIC_REFRESH_RETRY_SECONDS = DAILY_RETRY_LOCK_MAX_SECONDS


def bounded_step_timeout(seconds: float) -> float:
    """Clamp one recognition/wait/action window to the live safety budget."""

    return max(0.0, min(float(seconds), AUTOMATION_STEP_TIMEOUT_SECONDS))
