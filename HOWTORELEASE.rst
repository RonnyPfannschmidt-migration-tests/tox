==================
How to release tox
==================

This matches the current model that can be summarized as this:

* tox has no long lived branches.

* Pull requests get integrated into master by members of the project when they feel confident that this could be part of the next release. Small fix ups might be done right after merge instead of discussing back and forth to get minor problems fixed, to keep the workflow simple.

**Normal releases**: done from master when enough changes have accumulated (whatever that means at any given point in time).

**"Special" releases**: (in seldom cases when master has moved on and is not in a state where a quick release should be done from that state): the current release tag is checked out, the necessary fixes are cherry picked and a package with a patch release increase is built from that state. This is not very clean but seems good enough at the moment as it does not happen very often. If it does happen more often, this needs some rethinking (and rather into the direction of making less buggy releases than complicating release development/release process).

HOWTO
=====

Prerequisites
-------------

* Push rights for https://github.com/tox-dev/tox
* Release rights for https://pypi.org/project/tox/
* [optional] An account on https://m.devpi.net to upload the package under test
* A system with either tox + `bash <https://www.gnu.org/software/bash/>`_ or `vagrant <https://github.com/tox-dev/tox/blob/master/Vagrantfile>`_ (which contains tox + bash)
* Accountability: if you cut a release that breaks the CI builds of projects using tox, you are expected to fix this within a reasonable time frame (hours/days - not weeks/months) - if you don't feel quite capable of doing this yet, partner up with a more experienced member of the team and make sure they got your back if things break.

pypi/devpi configuration
------------------------

**note:** this is in a state of flux due to changes in pypi infrastructure and depending whether devpi push can be used or not. **Please keep this updated according to current process**

**Current process** pypi upload packages from `dist/` via twine.

If you want to use the scripts in `task/` you need a `.pypirc` with a correctly configured `pypi` section (see below). Otherwise just upload the release package which ever way you see fit.

[pypi] section in `.pypirc` should look somehow like this:

.. code-block:: ini

    [pypi]
    ;repository=https://upload.pypi.io/legacy/
    username=<your username>
    password=<your password>


to get info about the workflow invoke::

    tox -e pra

and you get a help message like::


    workflow: /home/oliver/work/tox/tox/tasks/pra.sh <command> [arg]
        prep <version>
        upload <devpi username>
        devpi-cloud-test <devpi username> (optional)
        release

... and go from there.

The script executes the necessary actions and asks for confirmation to go on before committing or tagging stuff. So there is no danger to dry run the process, as long as you don't call the final `release` command with packages in your dist/* - if you managed to screw things up entirely there is always `git reset --hard HEAD` at your service.

**note:** `pra` is short for "personal release assistant" :) - if you want to see what this involves or rather do everything by hand, please read the scripts in `tasks <https://github.com/tox-dev/tox/tree/master/tasks>`_.

"Special" releases
------------------

If it is necessary to build a special release, where the standard flow can't be used and setuptools_scm gets in the way, you can do::

    SETUPTOOLS_SCM_PRETEND_VERSION=X.X.X python setup.py sdist bdist_wheel

Get started with devpi cloud test
---------------------------------

Configure a repository as per-instructions on devpi-cloud-test_ to test the package on Travis_ and AppVeyor_. All test environments should pass.

If you don't want or can't do the cloud test step ...
-----------------------------------------------------

Run from multiple machines::

   devpi use https://m.devpi.net/<your devpi user name>/dev
   devpi test tox==<VERSION>

Check that tests pass for relevant combinations with::

   devpi list tox

Post release activities
-----------------------

Make sure to let the world know that a new version is out by whatever means you see fit.

As a minimum, send a release mail like outlined below to::

    testing-in-python@lists.idyll.org, tox-dev@python.org


feature release::

    The tox team is proud to announce the <VERSION> release!

    tox aims to automate and standardize testing in Python. It is part of a
    larger vision of easing the packaging, testing and release process of
    Python software.

    Details about the changes can be found in the CHANGELOG:

        https://pypi.org/project/tox/<VERSION>/#changelog

    For complete documentation, please visit:

        https://tox.readthedocs.io/en/<VERSION>

    As usual, you can upgrade from pypi via:

        pip install --upgrade tox

    or - if you also want to get pre release versions:

        pip install -upgrade --pre tox

    We thank all present and past contributors to tox. Have a look at https://github.com/tox-dev/tox/blob/master/CONTRIBUTORS to see who contributed.

    Happy toxing,
    the tox-dev team


bug fix release::

    The tox team is proud to announce the <VERSION> release!

    tox aims to automate and standardize testing in Python. It is part of a larger vision of easing the packaging, testing and release process of Python software.

    For details about the fix(es),please check the CHANGELOG:

        https://pypi.org/project/tox/<VERSION>/#changelog

    We thank all present and past contributors to tox. Have a look at https://github.com/tox-dev/tox/blob/master/CONTRIBUTORS to see who contributed.

    Happy toxing,
    the tox-dev team


.. _devpi-cloud-test: https://github.com/obestwalter/devpi-cloud-test
.. _AppVeyor: https://www.appveyor.com/
.. _Travis: https://travis-ci.org
