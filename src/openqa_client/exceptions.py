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
# Author: Adam Williamson <awilliam@redhat.com>

"""Custom exceptions used by openqa_client."""

from requests.exceptions import ConnectionError as RConnectionError


class OpenQAClientError(Exception):
    """Base class for openQA client errors."""

    pass


class ConnectionError(OpenQAClientError):
    """Error raised when server connection fails. Just passed through
    requests.exceptions.ConnectionError.
    """

    def __init__(self, err: RConnectionError) -> None:
        self.err = err


class RequestError(OpenQAClientError):
    """Error raised when a request fails (after retries). 3-tuple of
    method, URL, and status code.
    """

    def __init__(self, method: str, url: str, status_code: int) -> None:
        self.method = method
        self.url = url
        self.status_code = status_code
