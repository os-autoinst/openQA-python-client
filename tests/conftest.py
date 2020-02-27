# Copyright (C) 2016 Red Hat
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

try:
    from unittest import mock
except ImportError:
    import mock

import pytest

@pytest.yield_fixture(scope="function")
def config(config_hosts):
    """Creates a config file in a fake user home directory, at
    data/home/ under the tests directory. For each host in
    config_hosts we write an entry with the same key and secret,
    unless the host has 'nokey' in it, in which case we write an entry
    with no key or secret. Before the test, re-create the home dir,
    and patch os.path.expanduser to return it. After the test, delete
    it and clean up the other bits.
    """
    datadir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
    home = os.path.join(datadir, 'home')
    if os.path.exists(datadir):
        shutil.rmtree(datadir)
    confpath = os.path.join(home, '.config', 'openqa')
    os.makedirs(confpath)
    confpath = os.path.join(confpath, 'client.conf')
    content = []
    for host in config_hosts:
        if "nokey" in host:
            # don't write a key and secret for this host
            content.extend(["[{}]".format(host)])
        else:
            content.extend(["[{}]".format(host), "key = aaaaaaaaaaaaaaaa",
                            "secret = bbbbbbbbbbbbbbbb"])
    content = "\n".join(content)
    with open(confpath, 'w') as conffh:
        conffh.write(content)
    with mock.patch('os.path.expanduser', return_value=home, autospec=True):
        yield

    # teardown stuff
    if os.path.exists(datadir):
        shutil.rmtree(datadir)
