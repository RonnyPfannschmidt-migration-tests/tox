#!/usr/bin/env bash

set -e

DEVPI_USERNAME=${TOX_RELEASE_DEVPI_USERNAME:-obestwalter}
PYPI_USERNAME=${TOX_RELEASE_PYPI_USERNAME:-obestwalter}
RELEASE_REMOTE=${TOX_RELEASE_REMOTE:-upstream}

if [ -z "$1" ]; then
    echo "usage: $0 prep <version> -> test -> rel"
    exit 1
fi

if [ -z "$2" ]; then
    VERSION=$2
else
    VERSION=$(git describe --abbrev=0 --tags)
fi

dispatch () {
    if [ "$1" == "prep" ]; then
        if [ -z "$2" ]; then
            echo "usage: $0 prep <version>"
            exit 1
        fi
        prep $2
    elif [ "$1" == "test" ]; then
         devpi-upload
         cloud-test
    elif [ "$1" == "rel" ]; then
        rel
    else
        exit 1
    fi
}

prep () {
    python3.6 contrib/release-pre-process.py
    pip install git+git://github.com/avira/towncrier.git@add-pr-links
    towncrier --draft --version ${VERSION} | ${PAGER}
    tox --version
    echo "consolidate?"
    _confirm
    towncrier --yes --version ${VERSION}
    git add .
    git status
    _confirm
    git commit -m "towncrier generated changelog"
    rm dist/tox*
    python setup.py sdist bdist_wheel
    git tag ${VERSION}
}

devpi-upload () {
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

cloud-test () {
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

rel () {
    echo -n "publish "
    echo "upload to devpi: $(ls dist/*)"
    _confirm
    twine upload dist/tox-$1-py2.py3-none-any.whl dist/tox-$1.tar.gz
    git push ${RELEASE_REMOTE} master
    git push ${RELEASE_REMOTE} --tags
}

_confirm () {
    select confirmation in yes no; do
        if [ ${confirmation} == "no" ]; then
            exit 1
        else
            break
        fi
    done
}

dispatch $1 $2
