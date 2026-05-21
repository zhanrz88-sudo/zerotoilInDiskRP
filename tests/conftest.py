"""Pytest configuration for zerotoil tests.

Markers
-------
- ``unittest``  – Unit tests with mocked APIs. Run in CI (default).
- ``integrationtest`` – Require live internal API access (XPortal, XDS, DGrep).
- ``e2etest`` – Full TSG execution against a live or staged incident.

The default marker filter (``-m unittest``) is set in pyproject.toml so that
``pytest`` with no extra flags runs only unit tests — matching CI behaviour.

To run other categories locally::

    pytest -m integrationtest -v
    pytest -m "unittest or integrationtest" -v
    pytest -m "" -v   # run everything (clear the default filter)
"""

import pytest

# The three test-category markers used by zerotoil
_CATEGORY_MARKERS = frozenset({"unittest", "integrationtest", "e2etest"})


def pytest_collection_modifyitems(config, items):
    """Auto-apply the ``unittest`` marker to tests that have no category marker."""
    unittest_marker = pytest.mark.unittest
    for item in items:
        item_markers = {m.name for m in item.iter_markers()}
        if not item_markers & _CATEGORY_MARKERS:
            item.add_marker(unittest_marker)
