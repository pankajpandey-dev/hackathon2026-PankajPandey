from __future__ import annotations

from utils.env import env_float

CONFIDENCE_THRESHOLD = env_float("SHOPWAVE_CONFIDENCE_THRESHOLD", "0.6")
FAILURE_SIM_RATE = env_float("SHOPWAVE_TOOL_FAILURE_RATE", "0.12")
MAX_TOOL_RETRIES = 3