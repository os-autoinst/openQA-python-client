# Copyright (C) 2015 Red Hat
#
# This program is free software; you can redistribute it and/or modify
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
# Authors: Adam Williamson <awilliam@redhat.com>
#          Ludwig Nussel   <ludwig.nussel@suse.de>
#          Jan Sedlak      <jsedlak@redhat.com>

"""Main client functionality."""

import hashlib
import hmac
import os
import logging
import time

from six.moves.urllib.parse import urlparse, urlunparse
from six.moves import configparser
import requests

import openqa_client.exceptions
import openqa_client.const as oqc

logger = logging.getLogger(__name__)


## MAIN CLIENT CLASS


class OpenQA_Client(object):
    """A client for the OpenQA REST API; just handles API auth if
    needed and provides a couple of custom methods for convenience.
    """
    def __init__(self, server='', scheme=''):
        # Read in config files.
        config = configparser.ConfigParser()
        paths = ('/etc/openqa',
                 '{0}/.config/openqa'.format(os.path.expanduser('~')))
        config.read('{0}/client.conf'.format(path)
                    for path in paths)

        # If server not specified, default to the first one in the
        # configuration file. If no configuration file, default to
        # localhost. NOTE: this is different from the perl client, it
        # *always* defaults to localhost.
        if not server:
            try:
                server = config.sections()[0]
            except (configparser.MissingSectionHeaderError, IndexError):
                server = 'localhost'

        if server.startswith('http'):
            # Handle entries like [http://foo] or [https://foo]. The,
            # perl client does NOT handle these, so you shouldn't use
            # them. This client started out supporting this, though,
            # so it should continue to.
            if not scheme:
                scheme = urlparse(server).scheme
            server = urlparse(server).netloc

        if not scheme:
            if server in ('localhost', '127.0.0.1', '::1'):
                # Default to non-TLS for localhost; cert is unlikely to
                # be valid for 'localhost' and there's no MITM...
                scheme = 'http'
            else:
                scheme = 'https'

        self.baseurl = urlunparse((scheme, server, '', '', '', ''))

        # Get the API secrets from the config file.
        try:
            apikey = config.get(server, 'key')
            self.apisecret = config.get(server, 'secret')
        except configparser.Error:
            try:
                apikey = config.get(self.baseurl, 'key')
                self.apisecret = config.get(self.baseurl, 'secret')
            except configparser.Error:
                logger.debug("No API key for %s: only GET requests will be allowed", server)
                apikey = ''
                self.apisecret = ''

        # Create a Requests session and ensure some standard headers
        # will be used for all requests run through the session.
        self.session = requests.Session()
        headers = {}
        headers['Accept'] = 'json'
        if apikey:
            headers['X-API-Key'] = apikey
        self.session.headers.update(headers)

    def _add_auth_headers(self, request):
        """Add authentication headers to a PreparedRequest. See
        openQA/lib/OpenQA/client.pm for the authentication design.
        """
        if not self.apisecret:
            # Can't auth without an API key.
            return request
        # don't modify the original
        request = request.copy()
        timestamp = time.time()
        path = request.path_url.replace('%20', '+').replace('~', '%7E')
        apihash = hmac.new(
            self.apisecret.encode(), '{0}{1}'.format(path, timestamp).encode(), hashlib.sha1)
        headers = {}
        headers['X-API-Microtime'] = str(timestamp).encode()
        headers['X-API-Hash'] = apihash.hexdigest()
        request.headers.update(headers)
        return request

    def do_request(self, request, retries=5, wait=10):
        """Passed a requests.Request, prepare it with the necessary
        headers, submit it, and return the JSON output. You can use
        this directly instead of openqa_request() if you need to do
        something unusual. May raise ConnectionError or RequestError
        if the connection or the request fail in some way after
        'retries' attempts. 'wait' determines how long we wait between
        retries: on the *first* retry we wait exactly 'wait' seconds,
        on each subsequent retry the wait time is doubled, up to a
        max of 60 seconds between attempts.
        """
        prepared = self.session.prepare_request(request)
        authed = self._add_auth_headers(prepared)
        # We can't use the nice urllib3 Retry stuff, because openSUSE
        # 13.2 has a sadly outdated version of python-requests. We'll
        # have to do it ourselves.
        try:
            resp = self.session.send(authed)
            if not resp.ok:
                raise openqa_client.exceptions.RequestError(
                    request.method, resp.url, resp.status_code)
            return resp.json()
        except (requests.exceptions.ConnectionError,
                openqa_client.exceptions.RequestError) as err:
            if retries:
                logger.debug(
                    "do_request: request failed! Retrying in %s seconds...",
                    wait)
                logger.debug("Error: %s", err)
                time.sleep(wait)
                newwait = min(wait+wait, 60)
                return self.do_request(request, retries=retries-1, wait=newwait)
            elif isinstance(err, openqa_client.exceptions.RequestError):
                raise err
            elif isinstance(err, requests.exceptions.ConnectionError):
                raise openqa_client.exceptions.ConnectionError(err)

    def openqa_request(self, method, path, params=None, retries=5, wait=10, data=None):
        """Perform a typical openQA request, with an API path and some
        optional parameters. Use the data parameter instead of params if you
        need to pass lots of settings. It will post
        application/x-www-form-urlencoded data.
        """
        if not params:
            params = {}
        # As with the reference client, we assume relative paths are
        # relative to /api/v1.
        if not path.startswith('/'):
            path = '/api/v1/{0}'.format(path)

        method = method.upper()
        url = '{0}{1}'.format(self.baseurl, path)
        req = requests.Request(method=method, url=url, params=params, data=data)
        return self.do_request(req, retries=retries, wait=wait)

    def find_clones(self, jobs):
        """Given an iterable of job dicts, this will see if any of the
        jobs were cloned, and replace any that were cloned with the dicts
        of their clones, returning a list. It recurses - so if 3 was
        cloned as 4 and 4 was cloned as 5, you'll wind up with 5. If both
        a job and its clone are already in the iterable, the original will
        be removed.
        """
        jobs = list(jobs)
        while any(job['clone_id'] for job in jobs):
            toget = []
            ids = [job['id'] for job in jobs]
            # copy the list to iterate over it
            for job in list(jobs):
                if job['clone_id']:
                    logger.debug("Replacing job %s with clone %s", job['id'], job['clone_id'])
                    if job['clone_id'] not in ids:
                        toget.append(str(job['clone_id']))
                    jobs.remove(job)

            if toget:
                toget = ','.join(toget)
                # Get clones and add them to the list
                clones = self.openqa_request('GET', 'jobs', params={'ids': toget})['jobs']
                jobs.extend(clones)
        return jobs

    def get_jobs(self, jobs=None, build=None, filter_dupes=True):
        """Get job dicts. Either 'jobs' or 'build' must be specified.
        'jobs' should be iterable of job IDs (string or int). 'build'
        should be an openQA BUILD to get all the jobs for. If both are
        specified, 'jobs' will be used and 'build' ignored. If
        filter_dupes is True, cloned jobs will be replaced by their
        clones (see find_clones docstring) and duplicate jobs will be
        filtered out (using the upstream 'latest' query param).

        Unlike all previous 'job get' methods in this module, this one
        will happily return results for running jobs. All it does is
        get the specified dicts, filter them if filter_dupes is set,
        and return. If you only want completed jobs, filter the result
        yourself, or just use fedmsg to make sure you only call this
        when all the jobs you want are done.

        This method requires the server to be at least version 4.3 to
        work correctly.
        """
        if not build and not jobs:
            raise TypeError("iterate_jobs: either 'jobs' or 'build' must be specified")
        if jobs:
            jobs = [str(j) for j in jobs]
            # this gets all jobdicts with a single API query
            params = {'ids': ','.join(jobs)}
        else:
            params = {'build': build}
        if filter_dupes:
            params['latest'] = 'true'
        jobdicts = self.openqa_request('GET', 'jobs', params=params)['jobs']
        if filter_dupes:
            # sub out clones. when run on a BUILD this is superfluous
            # as 'latest' will always wind up finding the latest clone
            # but this is still useful if run on a jobs iterable and
            # the jobs in question have clones; 'latest' doesn't help
            # there as it only considers the jobs queried.
            jobdicts = self.find_clones(jobdicts)
        return jobdicts
