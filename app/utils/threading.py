"""Shared lock for audit log and escalation file writes."""

import threading

AUDIT_IO_LOCK = threading.Lock()
