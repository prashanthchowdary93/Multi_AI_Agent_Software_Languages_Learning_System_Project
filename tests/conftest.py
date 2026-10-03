"""
config file for pytest
where we have defined the fixtures which can be used directly in the test_deepeval.py
for agents evaluation
"""

import sys
from  pathlib import Path
import json
import pytest

#set the path to src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def pytest_configure(config):
    """Register custom markers so pytest doesn't warn about unknown marks."""
    config.addinivalue_line(
        "markers",
        "eval: marks tests as evaluation tests requiring Ollama (deselect with -m 'not eval')"
    )
    config.addinivalue_line(
        "markers",
        "unit: marks tests as fast unit tests with no external dependencies"
    )

@pytest.fixture
def closure_notes_content():
    """
    The content of the closures.md sample note.
    Used as retrieval context in faithfulness tests.
    """
    notes_path = Path(__file__).parent.parent / "study_materials/sample_notes/closures.md"
    if notes_path.exists():
        return notes_path.read_text(encoding="utf-8")

    # Fallback scenario ,  if the file doesn't exist
    return """
# Python Closures

A closure is a nested function that remembers variables from its enclosing scope.

Three requirements:
1. A nested (inner) function
2. The inner function refers to a variable from the enclosing scope
3. The enclosing function returns the inner function

Example:
def make_counter(start=0):
    count = start
    def increment():
        nonlocal count
        count += 1
        return count
    return increment
"""