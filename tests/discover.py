"""Test discovery and execution module."""

import os
import sys

import pytest


def run(*, auto_exit=True):
    """Run the test suite using pytest.

    Args:
        auto_exit: Whether to exit with the appropriate exit code after running tests

    Returns:
        True if tests passed, False otherwise
    """
    # Determine test directory relative to this file
    test_dir = os.path.dirname(os.path.abspath(__file__))

    # Run pytest with verbose output
    exit_code = pytest.main(["-v", test_dir])
    success = exit_code == 0

    if auto_exit:
        sys.exit(exit_code)

    return success


if __name__ == "__main__":
    run()
