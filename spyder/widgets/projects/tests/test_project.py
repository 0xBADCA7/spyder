# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#
"""
Tests for __init__.py
"""

# Test library imports
import pytest

# Local imports
from spyder.widgets.projects import EmptyProject


@pytest.fixture(scope='session')
def project_test(tmpdir_factory):
    """
    Fixture for create a temporary project (mdw).

    Returns:
        str: Path of temporary project dir.
    """
    p = tmpdir_factory.mktemp("test_project")
    path = str(p)
    project = EmptyProject(path)
    return path, project


def test_empty_project(project_test):
    path, project = project_test
    assert project.root_path == path

if __name__ == "__main__":
    pytest.main()
