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
# Author: Adam Williamson <awilliam@redhat.com>

"""Main client functionality."""

import hashlib
import hmac
import os
import logging
import requests
import time

from six.moves import configparser
from six.moves.urllib.parse import urlparse, urlunparse

import openqa_client.exceptions

logger = logging.getLogger(__name__)


## HELPER FUNCTIONS (may need to be split out if this gets bigger)


def get_latest_jobs(jobs):
    """This is a job de-duping function. There is some ambiguity
    about exactly what jobs are 'duplicates' in openQA, as it's
    developed somewhat organically and it's not clear what is
    convention, what is policy, what is technical limitation etc.
    It would probably be useful if openQA itself provided more
    capabilities here.

    openQA has some code that does approximately the same thing,
    backing the per-build 'Overview' you can get in the web UI.
    As I write this it lives in
    lib/OpenQA/WebAPI/Controller/Test.pm and is not externally
    usable. It uses a 'key' made up of TEST setting, FLAVOR
    setting, ARCH setting, and MACHINE setting. The overview is
    for a specific combination of DISTRI, VERSION and BUILD.
    We're going to reproduce that logic here.

    Passed a list of job dicts, this will return a list containing
    only the newest job for each key - it will filter out earlier
    runs of 'the same' test for each distri/version/build included
    in the list.
    """
    seen = list()
    newjobs = list()
    jobs.sort(key=lambda x:x['id'], reverse=True)
    for job in jobs:
        settings = job['settings']
        key = (settings['DISTRI'], settings['VERSION'], settings['BUILD'], settings['TEST'],
               settings['FLAVOR'], settings['ARCH'], settings['MACHINE'])
        if not key in seen:
            seen.append(key)
            newjobs.append(job)
    return newjobs


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
        except configparser.NoSectionError:
            try:
                apikey = config.get(self.baseurl, 'key')
                self.apisecret = config.get(self.baseurl, 'secret')
            except:
                logger.debug("No API key: only GET requests will be allowed")
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
        timestamp = time.time()
        path = request.path_url.replace('%20', '+').replace('~', '%7E')
        apihash = hmac.new(
            self.apisecret.encode(), '{0}{1}'.format(path, timestamp).encode(), hashlib.sha1)
        headers = {}
        headers['X-API-Microtime'] = str(timestamp).encode()
        headers['X-API-Hash'] = apihash.hexdigest()
        request.headers.update(headers)
        return request

    def do_request(self, request, retries=5, wait=5):
        """Passed a requests.Request, prepare it with the necessary
        headers, submit it, and return the JSON output. You can use
        this directly instead of openqa_request() if you need to do
        something unusual. May raise ConnectionError if it cannot
        connect to a server (including e.g. if this happens to get
        run on a system with no client config at all) or RequestError
        if the request fails in some way after 'retries' attempts,
        waiting 'wait' seconds between retries.
        """
        prepared = self.session.prepare_request(request)
        authed = self._add_auth_headers(prepared)
        # We can't use the nice urllib3 Retry stuff, because openSUSE
        # 13.2 has a sadly outdated version of python-requests. We'll
        # have to do it ourselves.
        try:
            resp = self.session.send(authed)
            while not resp.ok and retries:
                logger.debug("do_request: request failed! Retrying...")
                retries -= 1
                time.sleep(wait)
                resp = self.session.send(authed)
            if resp.ok:
                return resp.json()
            else:
                raise openqa_client.exceptions.RequestError(
                    request.method, resp.url, resp.status_code)
        except requests.exceptions.ConnectionError as err:
            raise openqa_client.exceptions.ConnectionError(err)

    def openqa_request(self, method, path, params={}, retries = 5, wait = 5):
        """Perform a typical openQA request, with an API path and some
        optional parameters.
        """
        # As with the reference client, we assume relative paths are
        # relative to /api/v1.
        if not path.startswith('/'):
            path = '/api/v1/{0}'.format(path)

        method = method.upper()
        url = '{0}{1}'.format(self.baseurl, path)
        req = requests.Request(method=method, url=url, params=params)
        return self.do_request(req, retries=retries, wait=wait)

    def wait_jobs(self, jobs, waittime=180, delay=60):
        """Wait up to 'waittime' minutes, checking every 'delay'
        seconds, for the specified jobs (an iterable of job IDs) to
        be 'done' or 'cancelled'. Returns a list of the job dicts
        (with the useless outer dict which just has a single 'job:'
        key stripped). You can also pass an existing iterable of
        job dicts as 'jobs': if they are all done the list will be
        returned immediately, unmodified, otherwise the ids will be
        yanked out and used and the waiting will proceed. If waittime
        is set to 0, we will query just once and either succeed or
        fail immediately.
        """
        # First check if we got a list of dicts and they're all done,
        # and return right away if so.
        try:
            done = [job['id'] for job in jobs if job['state'] in ('done', 'cancelled')]
            if len(done) == len(jobs):
                return jobs
            else:
                jobs = [job['id'] for job in jobs]
        except TypeError:
            # Job list is just IDs, not dicts
            pass

        waitstart = time.time()
        done = {}
        while True:
            for job in jobs:
                if job not in done:
                    path = 'jobs/{0}'.format(str(job))
                    jobdict = self.openqa_request('GET', path)['job']
                    if jobdict['state'] in ('done', 'cancelled'):
                        done[job] = jobdict

            if len(done) == len(jobs):
                return done.values()
            else:
                if time.time() - waitstart > waittime * 60:
                    raise openqa_client.exceptions.WaitError("Waited too long!")
                logger.debug("wait_jobs: jobs not all done, will retry in %s seconds", str(delay))
                time.sleep(delay)

    def iterate_jobs(self, jobs, waittime=180, delay=60):
        """Generator function: yields list of dictionaries of jobs
        as soon as they are finished (they reach 'done' or 'cancelled'
        state). When all jobs are finished, returns empty value (as
        generators should). It returns list of dicts (rather than dicts
        directly), so that parent function can report multiple jobs at
        once (when multiple jobs are finished during single query). When
        no jobs were finished since last query, it sleeps for 'delay'
        seconds and then tries again, until at least one job gets finished
        or 'waittime' timeout is reached. 'jobs' should be list of either
        IDs (string or int) of jobs or complete job dictionaries. If 'waittime'
        is set to 0, we will query just once and either succeed or
        fail immediately.
        """
        waitstart = time.time()
        done = []
        to_report = []
        jobs_count = len(jobs)

        try:
            # get list of jobs that are already finished and convert dicts to IDs along the way
            to_report = [job for job in jobs if job['state'] in ('done', 'cancelled')]
            jobs = [job['id'] for job in jobs if job not in to_report]
        except TypeError:
            # Job list is just IDs, not dicts
            pass

        jobs = [int(j) for j in jobs]

        while True:
            for job in jobs:
                if job not in done:
                    path = 'jobs/{0}'.format(str(job))
                    jobdict = self.openqa_request('GET', path)['job']
                    if jobdict['state'] in ('done', 'cancelled'):
                        to_report.append(jobdict)

            if to_report:
                # save list of jobs that were reported back to program and yield them
                done.extend([int(job['id']) for job in to_report])
                yield to_report
                to_report = []

            if len(done) >= jobs_count:
                return  # return ends generator

            if time.time() - waitstart > waittime * 60:
                waiting_for = [j for j in jobs if j not in done]
                raise openqa_client.exceptions.WaitError("Waited too long!", unfinished_jobs=waiting_for)
            else:
                time.sleep(delay)

    def wait_build_jobs(self, build, waittime=480, delay=60, filter_dupes=True):
        """Wait up to 'waittime' minutes, checking every 'delay'
        seconds, for jobs for the specified BUILD to appear and
        complete. This method waits for some jobs to appear for the
        specified BUILD at all, then hands off to wait_jobs() to wait
        for them to be complete. If waittime is set to 0, we will
        query just once and either succeed or fail immediately. If
        filter_dupes is True, duplicate jobs will be filtered out (see
        get_latest_jobs docstring).
        """
        waitstart = time.time()
        jobs = []
        while True:
            jobs = self.openqa_request('GET', 'jobs', params={'build': build})['jobs']
            if jobs and all(job['state'] in ('done', 'cancelled') for job in jobs):
                if filter_dupes:
                    jobs = get_latest_jobs(jobs)
                return jobs

            if time.time() - waitstart > waittime * 60:
                raise openqa_client.exceptions.WaitError("Waited too long!")
            logger.debug("wait_build_jobs: jobs not complete or no jobs yet for %s, will retry in %s seconds",
                         build, str(delay))
            time.sleep(delay)
