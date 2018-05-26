import io
import sys

import setuptools


def has_environment_marker_support():
    """
    Tests that setuptools has support for PEP-426 environment marker support.

    The first known release to support it is 0.7 (and the earliest on PyPI seems to be 0.7.2
    so we're using that), see: http://pythonhosted.org/setuptools/history.html#id142

    References:

    * https://wheel.readthedocs.org/en/latest/index.html#defining-conditional-dependencies
    * https://www.python.org/dev/peps/pep-0426/#environment-markers
    """
    import pkg_resources

    try:
        v = pkg_resources.parse_version(setuptools.__version__)
        return v >= pkg_resources.parse_version("0.7.2")
    except Exception as e:
        sys.stderr.write("Could not test setuptool's version: {}\n".format(e))
        return False


def get_long_description():
    with io.open("README.rst", encoding="utf-8") as f:
        with io.open("CHANGELOG.rst", encoding="utf-8") as g:
            return u"{}\n\n{}".format(f.read(), g.read())


def main():
    setuptools.setup(
        name="tox",
        description="virtualenv-based automation of test activities",
        long_description=get_long_description(),
        url="https://tox.readthedocs.org/",
        use_scm_version=True,
        license="http://opensource.org/licenses/MIT",
        platforms=["unix", "linux", "osx", "cygwin", "win32"],
        author="holger krekel",
        author_email="holger@merlinux.eu",
        packages=["tox"],
        entry_points={
            "console_scripts": ["tox=tox:cmdline", "tox-quickstart=tox._quickstart:main"]
        },
        python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
        setup_requires=["setuptools_scm"],
        install_requires=["py>=1.4.17", "pluggy>=0.3.0,<1.0", "six", "virtualenv>=1.11.2"],
        extras_require={
            "testing": [
                "pytest >= 3.0.0",
                "pytest-cov",
                "pytest-mock",
                "pytest-timeout",
                "pytest-xdist",
                "pyannotate",
            ],
            "docs": ["sphinx >= 1.6.3, < 2", "towncrier >= 17.8.0"],
            "lint": ["pre-commit == 1.8.2"],
            "publish": ["devpi", "twine"],
        },
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Framework :: tox",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Operating System :: POSIX",
            "Operating System :: Microsoft :: Windows",
            "Operating System :: MacOS :: MacOS X",
            "Topic :: Software Development :: Testing",
            "Topic :: Software Development :: Libraries",
            "Topic :: Utilities",
        ]
        + [
            ("Programming Language :: Python :: {}".format(x))
            for x in "2 2.7 3 3.4 3.5 3.6".split()
        ],
    )


if __name__ == "__main__":
    main()
