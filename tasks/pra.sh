#!/usr/bin/env bash

# Personal Release Assistant (TM)

set -e

if [ -z "$1" ]; then
    echo "workflow: $0 <command> [arg]"
    echo "    prep <version>"
    echo "    upload <devpi username>"
    echo "    test <devpi username> (optional)"
    echo "    release"
    exit 1
fi

if [ -z "$2" ]; then
    # only the prep step needs the version
    VERSION=$2
else
    # all other steps take it from tag created in prep
    VERSION=$(git describe --abbrev=0 --tags)
fi

dispatch () {
    if [ "$1" == "prep" ]; then
        if [ -z "$2" ]; then
            echo "usage: $0 prep <version>"
            exit 1
        fi
        prep
    elif [ "$1" == "upload" ]; then
         devpi_upload
    elif [ "$1" == "test" ]; then
         devpi_cloud_test
    elif [ "$1" == "release" ]; then
        pypi_upload
    else
        exit 1
    fi
}

prep () {
    python3.6 tasks/pre-process-changelog.py
    towncrier --draft --version ${VERSION}
    _confirm "towncrier news to be added o.k.?"
    tox --version
    _confirm "version of package o.k.?"
    towncrier --yes --version ${VERSION}
    git add --verbose .
    git status --verbose
    _confirm "changes to repository o.k.?"
    git commit -m "release preparation for ${VERSION}"
    _confirm "rm dist/*, build, git tag ${VERSION}"
    rm dist/tox*
    python setup.py sdist bdist_wheel
    git tag ${VERSION}
}

devpi_upload () {
    if [ ! -d dist ]; then
        echo "needs builds in dist. Build first."
        exit 1
    fi
    echo "loggging in to devpi $DEVPI_USERNAME"
    devpi login ${DEVPI_USERNAME}
    devpi use https://devpi.net/${DEVPI_USERNAME}/dev
    echo "upload to devpi: $(ls dist/*)"
    _confirm
    devpi upload dist/*
}

devpi_cloud_test () {
    cloudTestPath=../devpi-cloud-test-tox
    if [ ! -d "$cloudTestPath" ]; then
        echo "needs $cloudTestPath"
        exit 1
    fi
    echo "trigger devpi cloud tests for ${VERSION}?"
    _confirm
    cd ${cloudTestPath}
    dct trigger ${VERSION}
    xdg-open https://github.com/obestwalter/devpi-cloud-test-tox
    cd ../tox
}

# TODO get devpi push to work again
pypi_upload () {
    PACKAGES=$(ls dist/*)
    _confirm "upload to pypi: $PACKAGES"
    twine upload ${PACKAGES}
    git push upstream master
    git push upstream ${VERSION}
}

_confirm () {
    echo "please confirm: $1"
    select confirmation in yes no; do
        if [ ${confirmation} == "no" ]; then
            exit 1
        else
            break
        fi
    done
}

dispatch $1 $2
