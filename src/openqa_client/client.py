# Copyright Red Hat
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
import sys
from typing import Any, Dict, List, MutableMapping, NoReturn, Optional, Union, overload

from urllib.parse import urlparse, urlunparse
import configparser
import requests
import yaml

import openqa_client.exceptions

if sys.version_info >= (3, 8):
    from typing import Literal, TypedDict
else:  # pragma: no cover
    from typing_extensions import Literal, TypedDict  # pragma: no cover


logger = logging.getLogger(__name__)


RequestMethod = Literal["get", "put", "post", "delete", "GET", "PUT", "POST", "DELETE"]


class Job(TypedDict):
    """Response from openQA about a job."""

    #: settings of this job as reported in the webui
    settings: Dict[str, str]
    #: this jobs unique identifier
    id: int
    #: the unique identifier of the job as which this job has been cloned
    clone_id: int


## MAIN CLIENT CLASS


class OpenQA_Client:
    """A client for the OpenQA REST API; just handles API auth if
    needed and provides a couple of custom methods for convenience.

    Args:
        server: The URL or hostname of the openqa server.
                If not provided, will default to the first server in openqa's
                config files or localhost if none are present.
        scheme: The scheme used by the server.
                Extracted from the hostname by default.
        retries: A default value for the number of retries that will be
                 performed per request. This value is used if retries is not
                 provided to the respective method calls.
        wait: A default value for the time to wait between attempted requests
              in seconds. The value provided to the respective method calls
              takes precedence over this.
    """

    def __init__(
        self, server: str = "", scheme: str = "", retries: int = 5, wait: int = 10
    ) -> None:
        self.retries = retries
        self.wait = wait
        # Read in config files.
        config = configparser.ConfigParser()
        paths = ("/etc/openqa", f"{os.path.expanduser('~')}/.config/openqa")
        config.read(f"{path}/client.conf" for path in paths)

        # If server not specified, default to the first one in the
        # configuration file. If no configuration file, default to
        # localhost. NOTE: this is different from the perl client, it
        # *always* defaults to localhost.
        if not server:
            try:
                server = config.sections()[0]
            except (configparser.MissingSectionHeaderError, IndexError):
                server = "localhost"

        if server.startswith("http"):
            # Handle entries like [http://foo] or [https://foo]. The,
            # perl client does NOT handle these, so you shouldn't use
            # them. This client started out supporting this, though,
            # so it should continue to.
            if not scheme:
                scheme = urlparse(server).scheme
            server = urlparse(server).netloc

        if not scheme:
            if server in ("localhost", "127.0.0.1", "::1"):
                # Default to non-TLS for localhost; cert is unlikely to
                # be valid for 'localhost' and there's no MITM...
                scheme = "http"
            else:
                scheme = "https"

        self.baseurl = urlunparse((scheme, server, "", "", "", ""))

        # Get the API secrets from the config file.
        try:
            apikey = config.get(server, "key")
            self.apisecret = config.get(server, "secret")
        except configparser.Error:
            try:
                apikey = config.get(self.baseurl, "key")
                self.apisecret = config.get(self.baseurl, "secret")
            except configparser.Error:
                logger.debug("No API key for %s: only GET requests will be allowed", server)
                apikey = ""
                self.apisecret = ""

        # Create a Requests session and ensure some standard headers
        # will be used for all requests run through the session.
        self.session: requests.Session = requests.Session()
        headers = {}
        headers["Accept"] = "json"
        if apikey:
            headers["X-API-Key"] = apikey
        self.session.headers.update(headers)

    def _add_auth_headers(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        """Add authentication headers to a PreparedRequest. See
        openQA/lib/OpenQA/client.pm for the authentication design.
        """
        if not self.apisecret:
            # Can't auth without an API key.
            return request
        # don't modify the original
        request = request.copy()
        timestamp = time.time()
        path = request.path_url.replace("%20", "+").replace("~", "%7E")
        apihash = hmac.new(self.apisecret.encode(), f"{path}{timestamp}".encode(), hashlib.sha1)
        headers: MutableMapping[str, str] = {}
        headers["X-API-Microtime"] = str(timestamp)
        headers["X-API-Hash"] = apihash.hexdigest()
        request.headers.update(headers)
        return request

    @overload
    def do_request(
        self,
        request: requests.Request,
        retries: Optional[int] = None,
        wait: Optional[Union[int, float]] = None,
        parse: Literal[False] = False,
    ) -> requests.Response:
        ...  # pragma: no cover

    @overload
    def do_request(
        self,
        request: requests.Request,
        retries: Optional[int] = None,
        wait: Optional[Union[int, float]] = None,
        parse: Literal[True] = True,
    ) -> Any:
        ...  # pragma: no cover

    def do_request(
        self,
        request: requests.Request,
        retries: Optional[int] = None,
        wait: Optional[Union[int, float]] = None,
        parse: bool = True,
    ) -> Union[Any, requests.Response]:
        """Passed a requests.Request, prepare it with the necessary
        headers, submit it, and return the parsed output (unless parse
        is False, in which case return the response for the caller to
        do whatever it likes with). You can use this directly instead
        of openqa_request() if you need to do something unusual. May
        raise ConnectionError or RequestError if the connection or the
        request fail in some way after 'retries' attempts. 'wait'
        determines how long we wait between retries: on the *first*
        retry we wait exactly 'wait' seconds, on each subsequent retry
        the wait time is doubled, up to a max of 60 seconds between
        attempts.

        If wait or retries are None, then the global values of this class are
        used or the defaults apply.
        """
        prepared = self.session.prepare_request(request)
        authed = self._add_auth_headers(prepared)

        if retries is None:
            retries = self.retries
        if wait is None:
            wait = self.wait
        # We can't use the nice urllib3 Retry stuff, because openSUSE
        # 13.2 has a sadly outdated version of python-requests. We'll
        # have to do it ourselves.
        try:
            resp = self.session.send(authed)
            if not resp.ok:
                raise openqa_client.exceptions.RequestError(
                    request.method, resp.url, resp.status_code
                )
            if not parse or resp.status_code == 204:
                return resp
            # check if the server sent us YAML when we asked for JSON
            contype = resp.headers.get("content-type", "")
            if contype.startswith("text/yaml"):
                # FullLoader should also be fine as we trust the devs,
                # but I doubt they're gonna put anything beyond
                # SafeLoader's capacity in the responses
                return yaml.load(resp.text, Loader=yaml.SafeLoader)
            return resp.json()
        except (requests.exceptions.ConnectionError, openqa_client.exceptions.RequestError) as err:
            if retries:
                logger.debug("do_request: request failed! Retrying in %s seconds...", wait)
                logger.debug("Error: %s", err)
                time.sleep(wait)
                newwait = min(wait + wait, 60)
                return self.do_request(request, retries=retries - 1, wait=newwait)
            if isinstance(err, openqa_client.exceptions.RequestError):
                raise err
            if isinstance(err, requests.exceptions.ConnectionError):
                raise openqa_client.exceptions.ConnectionError(err)
            assert False, "This code path must be unreachable"

    def openqa_request(
        self,
        method: RequestMethod,
        path: str,
        params: Any = None,
        retries: Optional[int] = None,
        wait: Optional[int] = None,
        data: Any = None,
    ):
        """Perform a typical openQA request, with an API path and some
        optional parameters. Use the data parameter instead of params if you
        need to pass lots of settings. It will post
        application/x-www-form-urlencoded data.

        If either params or data is a dictionary and contains the key "settings"
        (which is a list of dictionaries), then the entries of "settings"
        converted as follows before being sent:
        params = {
            "name": "something",
            "settings": [{"key": "varname", "value": "var_value"}]
        }
        becomes:
        params = {
            "name": "something",
            "settings[varname]": "var_value"
        }
        """
        if not params:
            params = {}

        # we have to work around a limitation in the API: when modifying job
        # groups, products, etc. that take a settings parameter, then this
        # settings parameter gets returned to us as a list like this:
        # [{"key": "varname", "value": "var_value"}]
        # But when we sent the reply back, we must send these settings in the
        # "top level" payload object like this:
        # "settings[varname]": "var_value"
        for payload in (params, data):
            if (
                payload is not None
                and isinstance(payload, dict)
                and "settings" in payload
                and isinstance(payload["settings"], list)
            ):
                settings = payload.pop("settings")
                for setting in settings:
                    payload[f"settings[{setting.get('key')}]"] = setting["value"]

        # As with the reference client, we assume relative paths are
        # relative to /api/v1.
        if not path.startswith("/"):
            path = f"/api/v1/{path}"

        url = f"{self.baseurl}{path}"
        req = requests.Request(method=method.upper(), url=url, params=params, data=data)
        return self.do_request(req, retries=retries, wait=wait, parse=True)

    def find_clones(self, jobs: List[Job]) -> List[Job]:
        """Given an iterable of job dicts, this will see if any of the
        jobs were cloned, and replace any that were cloned with the dicts
        of their clones, returning a list. It recurses - so if 3 was
        cloned as 4 and 4 was cloned as 5, you'll wind up with 5. If both
        a job and its clone are already in the iterable, the original will
        be removed.
        """
        jobs = list(jobs)
        while any(job["clone_id"] for job in jobs):
            toget = []
            ids = [job["id"] for job in jobs]
            # copy the list to iterate over it
            for job in list(jobs):
                if job["clone_id"]:
                    logger.debug("Replacing job %s with clone %s", job["id"], job["clone_id"])
                    if job["clone_id"] not in ids:
                        toget.append(str(job["clone_id"]))
                    jobs.remove(job)

            if toget:
                # Get clones and add them to the list
                clones = self.openqa_request("GET", "jobs", params={"ids": ",".join(toget)})["jobs"]
                jobs.extend(clones)
        return jobs

    @overload
    def get_jobs(self, jobs: Literal[None], build: Literal[None], filter_dupes: bool) -> NoReturn:
        ...  # pragma: no cover

    @overload
    def get_jobs(
        self, jobs: Optional[List[Union[str, int]]], build: Optional[str], filter_dupes: bool
    ):
        ...  # pragma: no cover

    def get_jobs(
        self,
        jobs: Optional[List[Union[str, int]]] = None,
        build: Optional[str] = None,
        filter_dupes: bool = True,
    ):
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
            # this gets all jobdicts with a single API query
            params = {"ids": ",".join(str(j) for j in jobs)}
        else:
            assert build is not None
            params = {"build": build}
        if filter_dupes:
            params["latest"] = "1"
        jobdicts = self.openqa_request("GET", "jobs", params=params)["jobs"]
        if filter_dupes:
            # sub out clones. when run on a BUILD this is superfluous
            # as 'latest' will always wind up finding the latest clone
            # but this is still useful if run on a jobs iterable and
            # the jobs in question have clones; 'latest' doesn't help
            # there as it only considers the jobs queried.
            jobdicts = self.find_clones(jobdicts)
        return jobdicts
