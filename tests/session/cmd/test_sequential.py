import json
import re
import sys
from typing import Any, Dict, List, Tuple, Union

import pytest
from re_assert import Matches
from virtualenv.discovery.py_info import PythonInfo

from tox import __version__
from tox.pytest import ToxProjectCreator


def test_run_ignore_cmd_exit_code(tox_project: ToxProjectCreator) -> None:
    cmd = [
        "- python -c 'import sys; print(\"magic fail\", file=sys.stderr); sys.exit(1)'",
        "python -c 'import sys; print(\"magic pass\"); sys.exit(0)'",
    ]
    project = tox_project({"tox.ini": f"[tox]\nno_package=true\n[testenv]\ncommands={cmd[0]}\n {cmd[1]}"})
    outcome = project.run("r", "-e", "py")
    outcome.assert_success()
    assert "magic pass" in outcome.out
    assert "magic fail" in outcome.err


def test_run_sequential_fail(tox_project: ToxProjectCreator) -> None:
    def _cmd(value: int) -> str:
        return f"python -c 'import sys; print(\"exit {value}\"); sys.exit({value})'"

    ini = f"[tox]\nenv_list=a,b\nno_package=true\n[testenv:a]\ncommands={_cmd(1)}\n[testenv:b]\ncommands={_cmd(0)}"
    project = tox_project({"tox.ini": ini})
    outcome = project.run("r", "-e", "a,b")
    outcome.assert_failed()
    reports = outcome.out.splitlines()[-3:]
    assert Matches(r"  evaluation failed :\( \(.* seconds\)") == reports[-1]
    assert Matches(r"  b: OK \(.*=setup\[.*\]\+cmd\[.*\] seconds\)") == reports[-2]
    assert Matches(r"  a: FAIL code 1 \(.*=setup\[.*\]\+cmd\[.*\] seconds\)") == reports[-3]


@pytest.mark.timeout(60)
@pytest.mark.integration
def test_result_json_sequential(tox_project: ToxProjectCreator) -> None:
    cmd = [
        "- python -c 'import sys; print(\"magic fail\", file=sys.stderr); sys.exit(1)'",
        "python -c 'import sys; print(\"magic pass\"); sys.exit(0)'",
    ]
    project = tox_project(
        {
            "tox.ini": f"[tox]\nenvlist=py\n[testenv]\npackage=wheel\ncommands={cmd[0]}\n {cmd[1]}",
            "setup.py": "from setuptools import setup\nsetup(name='a', version='1.0', py_modules=['run'],"
            "install_requires=['setuptools>44'])",
            "run.py": "print('run')",
            "pyproject.toml": '[build-system]\nrequires=["setuptools","wheel"]\nbuild-backend="setuptools.build_meta"',
        }
    )
    log = project.path / "log.json"
    outcome = project.run("r", "-vv", "-e", "py", "--result-json", str(log))
    outcome.assert_success()
    with log.open("rt") as file_handler:
        log_report = json.load(file_handler)

    py_info = PythonInfo.current_system()
    host_python = {
        "executable": py_info.system_executable,
        "extra_version_info": None,
        "implementation": py_info.implementation,
        "is_64": py_info.architecture == 64,
        "sysplatform": py_info.platform,
        "version": py_info.version,
        "version_info": list(py_info.version_info),
    }
    packaging_setup = get_cmd_exit_run_id(log_report, ".package-py", "setup")

    assert packaging_setup == [
        (0, "install"),
        (None, "_commands"),
        (None, "get_requires_for_build_wheel"),
        (0, "install"),
        (0, "freeze"),
    ]
    packaging_test = get_cmd_exit_run_id(log_report, ".package-py", "test")
    assert packaging_test == [(None, "build_wheel")]
    packaging_installed = log_report["testenvs"][".package-py"].pop("installed_packages")
    assert {i[: i.find("==")] for i in packaging_installed} == {"pip", "setuptools", "wheel"}

    py_setup = get_cmd_exit_run_id(log_report, "py", "setup")
    assert py_setup == [(0, "install"), (0, "install"), (0, "freeze")]  # install => 1 dep and 1 package
    py_test = get_cmd_exit_run_id(log_report, "py", "test")
    assert py_test == [(1, "commands[0]"), (0, "commands[1]")]
    packaging_installed = log_report["testenvs"]["py"].pop("installed_packages")
    expected_pkg = {"pip", "setuptools", "wheel", "a"}
    assert {i[: i.find("==")] if "@" not in i else "a" for i in packaging_installed} == expected_pkg
    install_package = log_report["testenvs"]["py"].pop("installpkg")
    assert re.match("^[a-fA-F0-9]{64}$", install_package.pop("sha256"))
    assert install_package == {"basename": "a-1.0-py3-none-any.whl", "type": "file"}

    expected = {
        "reportversion": "1",
        "toxversion": __version__,
        "platform": sys.platform,
        "testenvs": {
            "py": {"python": host_python},
            ".package-py": {"python": host_python},
        },
    }
    assert "host" in log_report
    assert log_report.pop("host")
    assert log_report == expected


def get_cmd_exit_run_id(report: Dict[str, Any], name: str, group: str) -> List[Tuple[Union[int, None], str]]:
    return [(i["retcode"], i["run_id"]) for i in report["testenvs"][name].pop(group)]
