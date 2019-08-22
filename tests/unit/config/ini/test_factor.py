from textwrap import dedent
from typing import List

import pytest

from tox.config.source.ini import filter_for_env, find_envs
from tox.pytest import ToxProjectCreator


def complex_example():
    return dedent(
        """
    default
    lines
    py: py only
    !py: not py
    {py,!pi}-{a,b}{,-dev},c: complex
    extra: extra
    more-default
    """
    )


def test_factor_env_discover():
    result = list(find_envs(complex_example()))
    assert result == [
        "py",
        "py-a",
        "py-a-dev",
        "py-b",
        "py-b-dev",
        "pi-a",
        "pi-a-dev",
        "pi-b",
        "pi-b-dev",
        "c",
        "extra",
    ]


@pytest.mark.parametrize("env", list(find_envs(complex_example())))
def test_factor_env_filter(env):
    text = complex_example()
    result = filter_for_env(text, name=env)
    assert "default" in result
    assert "lines" in result
    assert "more-default" in result
    if "py" in env:
        assert "py only" in result
        assert "not py" not in result
    else:
        assert "py only" not in result
        assert "not py" in result
    if "extra" == env:
        assert "extra" in result
    else:
        assert "extra" not in result
    if env in {"py-a", "py-a-dev", "py-b", "py-b-dev", "c"}:
        assert "complex" in result
    else:
        assert "complex" not in result


def test_factor_env_list(tox_project: ToxProjectCreator):
    project = tox_project(
        {
            "tox.ini": """
        [tox]
        env_list = {py27,py36}-django{ 15, 16 }{,-dev}, docs, flake
        """
        }
    )
    config = project.config()
    result = list(config)
    assert result == [
        "py27-django15",
        "py27-django15-dev",
        "py27-django16",
        "py27-django16-dev",
        "py36-django15",
        "py36-django15-dev",
        "py36-django16",
        "py36-django16-dev",
        "docs",
        "flake",
    ]


def test_simple_env_list(tox_project: ToxProjectCreator):
    project = tox_project(
        {
            "tox.ini": """
        [tox]
        env_list = docs, flake8
        """
        }
    )
    config = project.config()
    assert list(config) == ["docs", "flake8"]


def test_factor_config(tox_project: ToxProjectCreator):
    project = tox_project(
        {
            "tox.ini": """
        [tox]
        env_list = {py36,py37}-{django15,django16}
        [testenv]
        deps =
            pytest
            django15: Django>=1.5,<1.6
            django16: Django>=1.6,<1.7
            py36: unittest2
        """
        }
    )
    config = project.config()
    assert list(config) == ["py36-django15", "py36-django16", "py37-django15", "py37-django16"]
    for env in config.core["env_list"]:
        env_config = config[env]
        env_config.add_config(
            keys="deps", of_type=List[str], default=[], desc="deps", overwrite=True
        )
        deps = env_config["deps"]
        assert "pytest" in deps
        if "py36" in env:
            assert "unittest2" in deps
        if "django15" in env:
            assert "Django>=1.5,<1.6" in deps
        if "django16" in env:
            assert "Django>=1.6,<1.7" in deps


def test_factor_config_no_env_list_creates_env(tox_project: ToxProjectCreator):
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    project = tox_project(
        {
            "tox.ini": """
        [tox]
        env_list = py37-{django15,django16}
        [testenv]
        deps =
            pytest
            django15: Django>=1.5,<1.6
            django16: Django>=1.6,<1.7
            py36: unittest2
        """
        }
    )
    config = project.config()
    assert list(config) == ["py37-django15", "py37-django16", "py36"]
