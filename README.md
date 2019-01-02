[![Latest version on PyPi](https://badge.fury.io/py/tox.svg)](https://badge.fury.io/py/tox)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/tox.svg)](https://pypi.org/project/tox/)
[![Azure Pipelines build status](https://dev.azure.com/toxdev/tox/_apis/build/status/tox%20ci?branchName=master)](https://dev.azure.com/toxdev/tox/_build/latest?definitionId=9&branchName=master)
[![Test Coverage](https://api.codeclimate.com/v1/badges/425c19ab2169a35e1c16/test_coverage)](https://codeclimate.com/github/tox-dev/tox/code?sort=test_coverage)
[![Documentation status](https://readthedocs.org/projects/tox/badge/?version=latest&style=flat-square)](https://tox.readthedocs.io/en/latest/?badge=latest)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

<a href="https://tox.readthedocs.io">
    <img src="https://tox.readthedocs.io/en/latest/_static/img/tox.png" alt="tox logo" align="right" height="150">
</a>

# tox automation project

**Command line driven CI frontend and development task automation tool**

At its core tox povides a convenient way to run arbitrary commands in isolated environments to serve as a single entry point for build, test and release activities.

tox is highly [configurable](https://tox.readthedocs.io/en/latest/config.html) and [pluggable](https://tox.readthedocs.io/en/latest/plugins.html).

## How it works

![tox flow](https://tox.readthedocs.io/en/latest/_images/tox_flow.png)

## tox can be used for ...

* creating develepment environments
* running static code analysis and test tools
* automating package builds
* running tests against the package build by tox
* checking that packages install correctly with different Python versions/interpreters
* unifying Continuous Integration and command line based testing
* building and deploying project documentation
* release automation
* limit: your imagination

## Projects using tox

tox is widely used, so this is only a very small selection:

* [ansibele](https://github.com/ansible/ansible) (devpi and plugins/tools)
* [devpi](https://github.com/devpi) (devpi and plugins/tools)
* [django](https://github.com/django/django)
* [httpie](https://github.com/jakubroztocil/httpie)
* [pallets](https://github.com/pallets) (flask, jinja, etc)
* [pandas](https://github.com/pandas-dev/pandas)
* [pytest-dev](https://github.com/pytest-dev) (pytest and plugins/tools)
* [requests](https://github.com/requests/requests)
* [tox-dev](https://github.com/tox-dev) (obviously)
* [and many more](https://github.com/tox-dev/tox/network/dependents)

---

## Usage

# A simple example

To test a simple project that has some tests:

```ini
# content of: tox.ini , put in same dir as setup.py
[tox]
envlist = py27,py36

[testenv]
deps = pytest       # install pytest in the virtualenv where commands will be executed
commands =
    # whatever extra steps before testing might be necessary
    pytest          # or any other test runner that you might use
```

```console
$ tox

[lots of output from commands that were run]

__________________ summary _________________
  py27: commands succeeded
  py36: commands succeeded
```

## Misc

Contributions are welcome, see [contributing](https://github.com/tox-dev/tox/blob/master/CONTRIBUTING.rst) and our [Contributor Covenant Code of Conduct](https://github.com/tox-dev/tox/blob/master/CODE_OF_CONDUCT.md).

* [docs are here](https://tox.readthedocs.org)
* [code is here](https://github.com/tox-dev/tox)
* [issue tracker is here](https://github.com/tox-dev/tox/issues)
* [License is MIT](https://github.com/tox-dev/tox/blob/master/LICENSE)
