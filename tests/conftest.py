"""Shared pytest configuration.

``regenerate`` is gated behind ALLOW_REGENERATE (off by default so a shared
deployment can't let one client reseed the pool for everyone). Enable it for the
test session — before ``random_mcp_server.server`` is imported — so the
regenerate scenarios exercise the tool. The default-off / hidden behavior is
covered explicitly in ``test_feature_flags.py``.
"""

import os

os.environ.setdefault("ALLOW_REGENERATE", "1")
