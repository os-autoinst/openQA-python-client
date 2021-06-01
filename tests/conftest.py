# Copyright Red Hat
#
# This file is part of openQA-python-client.
#
# openQA-python-client is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Adam Williamson <awilliam@redhat.com>

# these are all kinda inappropriate for pytest patterns
# pylint: disable=no-init, protected-access, no-self-use, unused-argument

"""Test configuration and fixtures."""

import os
import shutil
from unittest import mock

import pytest


def _config_teardown(datadir):
    if os.path.exists(datadir):
        shutil.rmtree(datadir)


def _config_setup(hosts):
    """Creates a config file in a fake user home directory, at
    data/home/ under the tests directory. For each host in hosts we
    write an entry with the same key and secret, unless the host has
    'nokey' in it, in which case we write an entry with no key or
    secret. Before doing this, re-create the home dir.
    """
    datadir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
    home = os.path.join(datadir, "home")
    _config_teardown(datadir)
    confpath = os.path.join(home, ".config", "openqa")
    os.makedirs(confpath)
    confpath = os.path.join(confpath, "client.conf")
    content = []
    for host in hosts:
        if "nokey" in host:
            # don't write a key and secret for this host
            content.extend([f"[{host}]"])
        else:
            content.extend([f"[{host}]", "key = aaaaaaaaaaaaaaaa", "secret = bbbbbbbbbbbbbbbb"])
    content = "\n".join(content)
    with open(confpath, "w") as conffh:
        conffh.write(content)
    return (datadir, home)


@pytest.fixture(scope="function")
def config(config_hosts):
    """Create config file via _config_setup, using list of hosts
    passed in via arg (intended for parametrization). Patch
    os.path.expanduser to return the home dir, then teardown on test
    completion.
    """
    (datadir, home) = _config_setup(config_hosts)
    with mock.patch("os.path.expanduser", return_value=home, autospec=True):
        yield
    _config_teardown(datadir)


@pytest.fixture(scope="function")
def simple_config():
    """Create config file via _config_setup, with a single host. Patch
    os.path.expanduser to return the home dir, then teardown on test
    completion.
    """
    (datadir, home) = _config_setup(["openqa.fedoraproject.org"])
    with mock.patch("os.path.expanduser", return_value=home, autospec=True):
        yield
    _config_teardown(datadir)


@pytest.fixture(scope="function")
def empty_config():
    """Create empty config file via _config_setup. Patch
    os.path.expanduser to return the home dir, then teardown on test
    completion.
    """
    (datadir, home) = _config_setup([])
    with mock.patch("os.path.expanduser", return_value=home, autospec=True):
        yield
    _config_teardown(datadir)
