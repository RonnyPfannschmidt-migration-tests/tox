"""Tests that require external access (e.g. pip install, virtualenv creation)"""
import os
import subprocess
import sys

import pytest
from pathlib2 import Path

from tests.lib import need_git


@pytest.mark.network
def test_package_isolated_build_setuptools(initproj, cmd):
    initproj(
        "package_toml_setuptools-0.1",
        filedefs={
            "tox.ini": """
                    [tox]
                    isolated_build = true
                    [testenv:.package]
                    basepython = python
                """,
            "pyproject.toml": """
                    [build-system]
                    requires = ["setuptools >= 35.0.2", "setuptools_scm >= 2.0.0, <3"]
                    build-backend = "setuptools.build_meta"
                    """,
        },
    )
    run(cmd, "package_toml_setuptools-0.1.tar.gz")


@pytest.mark.network
@need_git
@pytest.mark.skipif(sys.version_info < (3, 0), reason="flit is Python 3 only")
def test_package_isolated_build_flit(initproj, cmd):
    initproj(
        "package_toml_flit-0.1",
        filedefs={
            "tox.ini": """
                    [tox]
                    isolated_build = true
                    [testenv:.package]
                    basepython = python
                """,
            "pyproject.toml": """
                    [build-system]
                    requires = ["flit"]
                    build-backend = "flit.buildapi"

                    [tool.flit.metadata]
                    module = "package_toml_flit"
                    author = "Happy Harry"
                    author-email = "happy@harry.com"
                    home-page = "https://github.com/happy-harry/is"
                    """,
            ".gitignore": ".tox",
        },
        add_missing_setup_py=False,
    )
    env = os.environ.copy()
    env["GIT_COMMITTER_NAME"] = "committer joe"
    env["GIT_AUTHOR_NAME"] = "author joe"
    env["EMAIL"] = "joe@example.com"
    subprocess.check_call(["git", "init"], env=env)
    subprocess.check_call(["git", "add", "-A", "."], env=env)
    subprocess.check_call(["git", "commit", "-m", "first commit", "--no-gpg-sign"], env=env)

    run(cmd, "package_toml_flit-0.1.tar.gz")


@pytest.mark.network
@pytest.mark.skipif(sys.version_info < (3, 0), reason="poetry is Python 3 only")
def test_package_isolated_build_poetry(initproj, cmd):
    initproj(
        "package_toml_poetry-0.1",
        filedefs={
            "tox.ini": """
                    [tox]
                    isolated_build = true
                    [testenv:.package]
                    basepython = python
                """,
            "pyproject.toml": """
                    [build-system]
                    requires = ["poetry>=0.12"]
                    build-backend = "poetry.masonry.api"

                    [tool.poetry]
                    name = "package_toml_poetry"
                    version = "0.1.0"
                    description = ""
                    authors = ["Name <email@email.com>"]

                    """,
            ".gitignore": ".tox",
        },
        add_missing_setup_py=False,
    )
    run(cmd, "package_toml_poetry-0.1.0.tar.gz")


def run(cmd, package):
    result = cmd("--sdistonly", "-e", "py", "-v", "-v")

    assert result.ret == 0, result.out
    package_venv = (Path() / ".tox" / ".package").resolve()
    assert ".package create: {}".format(package_venv) in result.outlines, result.out
    assert "write config to {}".format(package_venv / ".tox-config1") in result.out, result.out
    package_path = (Path() / ".tox" / "dist" / package).resolve()
    assert package_path.exists()

    package_path.unlink()

    # second call re-uses
    result2 = cmd("--sdistonly", "-e", "py", "-v", "-v")

    assert result2.ret == 0, result2.out
    assert (
        ".package reusing: {}".format(package_venv) in result2.outlines
    ), "Second call output:\n{}First call output:\n{}".format(result2.out, result.out)
    assert package_path.exists()
