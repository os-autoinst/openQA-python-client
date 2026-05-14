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

# these are all kinda inappropriate for pytest patterns
# pylint: disable=old-style-class, no-init, protected-access, no-self-use, unused-argument
# pylint: disable=invalid-name, too-few-public-methods, too-many-public-methods, too-many-lines

"""Tests for the main client code."""

import freezegun
import pytest
import requests
from pytest_mock import MockerFixture

import openqa_client.client as oqc
import openqa_client.exceptions as oqe


class TestClient:
    """Tests for the client library."""

    @pytest.mark.usefixtures("config")
    @pytest.mark.parametrize(
        "config_hosts",
        [
            ["localhost"],
            ["openqa.fedoraproject.org"],
            ["localhost", "openqa.fedoraproject.org"],
            ["openqa.fedoraproject.org", "localhost"],
            ["openqa.nokey.org", "localhost", "openqa.fedoraproject.org"],
            ["http://openqa.fedoraproject.org", "openqa.fedoraproject.org"],
            ["https://openqa.fedoraproject.org", "localhost"],
        ],
    )
    def test_config_hosts(self, config_hosts: list[str]) -> None:
        """Test handling config files with various different hosts.

        Sometimes one host, sometimes more.
        """
        client = oqc.OpenQA_Client()
        # we expect default scheme 'http' for localhost, specified
        # scheme if there is one, 'https' for all else
        if config_hosts[0] == "localhost":
            scheme = "http://"
        elif config_hosts[0].startswith("http"):
            scheme = ""
        else:
            scheme = "https://"
        assert client.baseurl == f"{scheme}{config_hosts[0]}"
        assert client.session.headers["Accept"] == "json"
        # this should be set for all but the 'nokey' case
        if "nokey" in config_hosts[0]:
            assert "X-API-Key" not in client.session.headers
        else:
            assert client.session.headers["X-API-Key"] == "aaaaaaaaaaaaaaaa"
            assert client.apisecret == "bbbbbbbbbbbbbbbb"
        # check we override the config file priority but use the key
        # if server and scheme specified
        client = oqc.OpenQA_Client(server="openqa.fedoraproject.org", scheme="http")
        assert client.baseurl == "http://openqa.fedoraproject.org"
        if "openqa.fedoraproject.org" in config_hosts:
            assert client.session.headers["X-API-Key"] == "aaaaaaaaaaaaaaaa"
            assert client.apisecret == "bbbbbbbbbbbbbbbb"
        else:
            assert "X-API-Key" not in client.session.headers

    @pytest.mark.usefixtures("empty_config")
    def test_noconfig_host(self) -> None:
        """Test with empty config file (should use localhost)."""
        client = oqc.OpenQA_Client()
        assert client.baseurl == "http://localhost"
        assert "X-API-Key" not in client.session.headers

    @pytest.mark.usefixtures("simple_config")
    @freezegun.freeze_time("2020-02-27")
    def test_add_auth_headers(self) -> None:
        """Test _add_auth_headers."""
        client = oqc.OpenQA_Client()
        # this weird build value tests tilde substitution in hash
        params = {"build": "foo~", "latest": "1"}
        # this (incorrect) URL tests space substitution in hash
        request = requests.Request(
            url=client.baseurl + "/api/v1/jobs ", method="GET", params=params
        )
        prepared = client.session.prepare_request(request)
        authed = client._add_auth_headers(prepared)  # noqa: SLF001
        assert prepared.headers != authed.headers
        assert authed.headers["X-API-Hash"] == "71373f0a57118b120d1915ccc0a24ae2cc112ad3"
        assert authed.headers["X-API-Microtime"] == "1582761600.0"
        # with no key/secret, request should be returned unmodified
        client = oqc.OpenQA_Client("localhost")
        request = requests.Request(
            url=client.baseurl + "/api/v1/jobs ", method="GET", params=params
        )
        prepared = client.session.prepare_request(request)
        authed = client._add_auth_headers(prepared)  # noqa: SLF001
        assert prepared.headers == authed.headers

    @pytest.mark.usefixtures("simple_config")
    def test_do_request_ok(self, mocker: MockerFixture) -> None:
        """Test do_request (normal, success case)."""
        fakesend = mocker.patch("requests.sessions.Session.send", autospec=True)
        client = oqc.OpenQA_Client()
        params = {"id": "1"}
        request = requests.Request(url=client.baseurl + "/api/v1/jobs", method="GET", params=params)
        resp = client.do_request(request)
        # check request was authed. Note: [0][0] is self
        assert "X-API-Key" in fakesend.call_args[0][1].headers
        assert "X-API-Hash" in fakesend.call_args[0][1].headers
        assert "X-API-Microtime" in fakesend.call_args[0][1].headers
        # check URL looks right
        assert fakesend.call_args[0][1].url == "https://openqa.fedoraproject.org/api/v1/jobs?id=1"
        # do_request returns the raw response without parsing
        assert resp is fakesend.return_value
        assert len(fakesend.return_value.method_calls) == 0

    @pytest.mark.usefixtures("simple_config")
    def test_do_request_ok_yaml(self, mocker: MockerFixture) -> None:
        """Test _parse_response (with YAML response)."""
        fakeresp = mocker.MagicMock()
        fakeresp.headers.get.return_value = "text/yaml,encoding=utf-8"
        fakeresp.text = "defaults:\n  arm:\n    machine: ARM"
        client = oqc.OpenQA_Client()
        ret = client._parse_response(fakeresp)  # noqa: SLF001
        # check we did not call .json() on response
        fakeresp.json.assert_not_called()
        # check we parsed the response
        assert ret == {"defaults": {"arm": {"machine": "ARM"}}}

    @pytest.mark.usefixtures("simple_config")
    def test_do_request_not_changed(self, mocker: MockerFixture) -> None:
        """Test openqa_request when receiving a 204 No Content reply.

        204 is handled in openqa_request (not do_request) because it is a
        server-side constraint — no body to parse — rather than a caller
        choice to skip parsing.
        """
        fakesend = mocker.patch("requests.sessions.Session.send", autospec=True)
        fakeresp = fakesend.return_value
        fakeresp.ok = True
        fakeresp.status_code = 204
        fakeresp.text = ""
        client = oqc.OpenQA_Client()
        ret = client.openqa_request("PUT", "job_templates_scheduling/1")
        assert len(fakeresp.method_calls) == 0, "no methods must be called on response"
        assert ret == fakesend.return_value, (
            "openqa_request should have returned the response itself"
        )

    @pytest.mark.usefixtures("simple_config")
    def test_do_request_502(self, mocker: MockerFixture) -> None:
        """Test do_request (response not OK and in the retry list, default retries)."""
        fakesend = mocker.patch("requests.sessions.Session.send", autospec=True)
        fakesleep = mocker.patch("time.sleep", autospec=True)
        fakeresp = fakesend.return_value
        fakeresp.ok = False
        fakeresp.status_code = 502
        client = oqc.OpenQA_Client()
        params = {"id": "1"}
        request = requests.Request(url=client.baseurl + "/api/v1/jobs", method="GET", params=params)
        # if response is not OK, we should raise RequestError
        with pytest.raises(oqe.RequestError):
            client.do_request(request)
        # we should also have retried 5 times, with a wait based on 10
        assert fakesend.call_count == 6
        assert fakesleep.call_count == 5
        sleeps = [call[0][0] for call in fakesleep.call_args_list]
        assert sleeps == [10, 20, 40, 60, 60]

    @pytest.mark.usefixtures("simple_config")
    def test_do_request_404(self, mocker: MockerFixture) -> None:
        """Test do_request (response not OK but not in the retry list, default retries)."""
        fakesend = mocker.patch("requests.sessions.Session.send", autospec=True)
        fakesleep = mocker.patch("time.sleep", autospec=True)
        fakeresp = fakesend.return_value
        fakeresp.ok = False
        fakeresp.status_code = 404
        client = oqc.OpenQA_Client()
        params = {"id": "1"}
        request = requests.Request(url=client.baseurl + "/api/v1/jobs", method="GET", params=params)
        # if response is not OK, we should raise RequestError
        with pytest.raises(oqe.RequestError):
            client.do_request(request)
        # we should not have retried
        assert fakesend.call_count == 1
        assert fakesleep.call_count == 0

    @pytest.mark.usefixtures("simple_config")
    def test_do_request_error(self, mocker: MockerFixture) -> None:
        """Test do_request (send raises exception, custom retries)."""
        fakesend = mocker.patch(
            "requests.sessions.Session.send",
            autospec=True,
            side_effect=requests.exceptions.ConnectionError("foo"),
        )
        fakesleep = mocker.patch("time.sleep", autospec=True)
        client = oqc.OpenQA_Client()
        params = {"id": "1"}
        request = requests.Request(url=client.baseurl + "/api/v1/jobs", method="GET", params=params)
        # if send raises ConnectionError, we should raise ours
        with pytest.raises(oqe.ConnectionError):
            client.do_request(request, retries=2, wait=5)
        # we should also have retried 2 times, with a wait based on 5
        assert fakesend.call_count == 3
        assert fakesleep.call_count == 2
        sleeps = [call[0][0] for call in fakesleep.call_args_list]
        assert sleeps == [5, 10]

    @pytest.mark.usefixtures("simple_config")
    def test_openqa_request(self, mocker: MockerFixture) -> None:
        """Test openqa_request."""
        fakedo = mocker.patch("openqa_client.client.OpenQA_Client.do_request", autospec=True)
        # configure the mock response so openqa_request's parsing logic
        # does not fall into yaml.load with a MagicMock object
        fakedo.return_value.status_code = 200
        fakedo.return_value.headers.get.return_value = "application/json"
        fakedo.return_value.json.return_value = {}
        client = oqc.OpenQA_Client()
        params = {"id": "1"}
        client.openqa_request("get", "jobs", params=params, retries=2, wait=5)
        # check we called do_request right. Note: [0][0] is self
        assert fakedo.call_args[0][1].url == "https://openqa.fedoraproject.org/api/v1/jobs"
        assert fakedo.call_args[0][1].params == {"id": "1"}
        assert fakedo.call_args[1]["retries"] == 2
        assert fakedo.call_args[1]["wait"] == 5
        # check requests with no params work
        fakedo.reset_mock()
        client.openqa_request("get", "jobs", retries=2, wait=5)
        assert fakedo.call_args[0][1].url == "https://openqa.fedoraproject.org/api/v1/jobs"
        assert fakedo.call_args[0][1].params == {}
        assert fakedo.call_args[1]["retries"] == 2
        assert fakedo.call_args[1]["wait"] == 5
        # check requests with data work
        fakedo.reset_mock()
        client.openqa_request("get", "jobs", data=params)
        prepped = fakedo.call_args[0][1].prepare()
        assert prepped.body == "id=1"
        assert prepped.headers == {
            "Content-Length": "4",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        # check requests with json work
        fakedo.reset_mock()
        client.openqa_request("get", "jobs", json=params)
        prepped = fakedo.call_args[0][1].prepare()
        assert prepped.body == b'{"id": "1"}'
        assert prepped.headers == {"Content-Length": "11", "Content-Type": "application/json"}

    @pytest.mark.usefixtures("simple_config")
    def test_openqa_request_retries(self, mocker: MockerFixture) -> None:
        """Test the handling of wait & retries when using openqa_request."""
        fakesend = mocker.patch(
            "requests.sessions.Session.send",
            autospec=True,
            side_effect=requests.exceptions.ConnectionError("foo"),
        )
        fakesleep = mocker.patch("time.sleep", autospec=True)
        client = oqc.OpenQA_Client(retries=3)

        with pytest.raises(oqe.ConnectionError):
            client.openqa_request("get", "jobs", wait=42)

        assert fakesend.call_count == 4, "expected the class global retries to be used"
        assert fakesleep.call_count == 3
        sleeps = [call[0][0] for call in fakesleep.call_args_list]
        # sleep time is capped at 60s
        assert sleeps == [42, 60, 60]

        fakesend.reset_mock()
        fakesleep.reset_mock()

        with pytest.raises(oqe.ConnectionError):
            client.openqa_request("get", "jobs", retries=1)

        assert fakesend.call_count == 2, (
            "expected the retries value from the method to take precedence"
        )
        assert fakesleep.call_count == 1
        sleeps = [call[0][0] for call in fakesleep.call_args_list]
        assert sleeps == [10], "expected class default for wait to be used"

    @pytest.mark.usefixtures("simple_config")
    def test_openqa_request_settings_addition(self, mocker: MockerFixture) -> None:
        """Test openqa_request's handling of the 'settings' parameter."""
        fakedo = mocker.patch("openqa_client.client.OpenQA_Client.do_request", autospec=True)
        fakedo.return_value.status_code = 200
        fakedo.return_value.headers.get.return_value = "application/json"
        fakedo.return_value.json.return_value = {}
        client = oqc.OpenQA_Client()
        test_suite_params = {
            "id": "1",
            "name": "some_suite",
            "settings": [
                {
                    "key": "PUBLISH_HDD_1",
                    "value": "%DISTRI%-%VERSION%-%ARCH%-%BUILD%.qcow2",
                },
                {"key": "START_AFTER_TEST", "value": "fedora_rawhide_qcow2"},
            ],
        }
        client.openqa_request("POST", "test_suites", params=test_suite_params)
        # check we called do_request right. Note: [0][0] is self
        assert fakedo.call_args[0][1].url == "https://openqa.fedoraproject.org/api/v1/test_suites"
        assert fakedo.call_args[0][1].params == {
            "id": "1",
            "name": "some_suite",
            "settings": {
                "PUBLISH_HDD_1": "%DISTRI%-%VERSION%-%ARCH%-%BUILD%.qcow2",
                "START_AFTER_TEST": "fedora_rawhide_qcow2",
            },
        }
        # check requests with a string payload
        fakedo.reset_mock()
        client.openqa_request("put", "test_suites", data="settings")
        assert fakedo.call_args[0][1].params == {}
        assert fakedo.call_args[0][1].data == "settings"

    @pytest.mark.usefixtures("simple_config")
    def test_not_prepend_api_route(self, mocker: MockerFixture) -> None:
        """Test openqa_request not prepending the /api/v1 string for absolute routes."""
        fakedo = mocker.patch("openqa_client.client.OpenQA_Client.do_request", autospec=True)
        fakedo.return_value.status_code = 200
        fakedo.return_value.headers.get.return_value = "application/json"
        fakedo.return_value.json.return_value = {}
        client = oqc.OpenQA_Client()
        client.openqa_request("GET", "/absolute_url")
        assert fakedo.call_args[0][1].url == "https://openqa.fedoraproject.org/absolute_url"

    @pytest.mark.usefixtures("simple_config")
    def test_find_clones(self, mocker: MockerFixture) -> None:
        """Test find_clones."""
        fakerequest = mocker.patch(
            "openqa_client.client.OpenQA_Client._openqa_request_json", autospec=True
        )
        client = oqc.OpenQA_Client()
        # test data: three jobs with clones, one included in the data,
        # two not
        jobs = [
            {"id": 1, "name": "foo", "result": "failed", "clone_id": 2},
            {"id": 2, "name": "foo", "result": "passed", "clone_id": None},
            {"id": 3, "name": "bar", "result": "failed", "clone_id": 4},
            {"id": 5, "name": "moo", "result": "failed", "clone_id": 6},
        ]
        # set the mock to return the additional jobs when we ask
        fakerequest.return_value = {
            "jobs": [
                {"id": 4, "name": "bar", "result": "passed", "clone_id": None},
                {"id": 6, "name": "moo", "result": "passed", "clone_id": None},
            ]
        }
        ret = client.find_clones(jobs)
        assert ret == [
            {"id": 2, "name": "foo", "result": "passed", "clone_id": None},
            {"id": 4, "name": "bar", "result": "passed", "clone_id": None},
            {"id": 6, "name": "moo", "result": "passed", "clone_id": None},
        ]
        # check we actually requested the additional job correctly
        assert fakerequest.call_count == 1
        assert fakerequest.call_args[0][1] == "GET"
        assert fakerequest.call_args[0][2] == "jobs"
        assert fakerequest.call_args[1]["params"] == {"ids": "4,6"}

    @pytest.mark.usefixtures("simple_config")
    def test_get_jobs(self, mocker: MockerFixture) -> None:
        """Test get_jobs."""
        fakerequest = mocker.patch(
            "openqa_client.client.OpenQA_Client._openqa_request_json", autospec=True
        )
        fakeclones = mocker.patch("openqa_client.client.OpenQA_Client.find_clones", autospec=True)
        client = oqc.OpenQA_Client()
        with pytest.raises(TypeError):
            client.get_jobs()
        client.get_jobs(jobs=[1, 2])
        assert fakerequest.call_args[0][1] == "GET"
        assert fakerequest.call_args[0][2] == "jobs"
        assert fakerequest.call_args[1]["params"] == {"ids": "1,2", "latest": "1"}
        assert fakeclones.call_count == 1
        client.get_jobs(build="foo", filter_dupes=False)
        assert fakerequest.call_args[0][1] == "GET"
        assert fakerequest.call_args[0][2] == "jobs"
        assert fakerequest.call_args[1]["params"] == {"build": "foo"}
        assert fakeclones.call_count == 1

    def test_client_errors(self) -> None:
        """Test creation of exceptions."""
        template_error = '{"error":"fail"}'
        err = oqe.RequestError("GET", "http://localhost", 404, template_error)
        assert err.args[0] == "GET"
        assert err.args[1] == "http://localhost"
        assert err.args[2] == 404
        assert err.method == "GET"
        assert err.url == "http://localhost"
        assert err.status_code == 404
        assert err.text == template_error

        err = oqe.ConnectionError("oh no")
        assert err.args[0] == "oh no"
        assert err.err == "oh no"

    def test_get_latest_build(self, mocker: MockerFixture) -> None:
        """Test get_latest_build."""
        fakerequest = mocker.patch(
            "openqa_client.client.OpenQA_Client._openqa_request_json", autospec=True
        )
        client = oqc.OpenQA_Client()
        fakerequest.return_value = {"build_results": [{"all_passed": 0, "build": "1"}]}
        ret = client.get_latest_build(42)
        # returns default when no passed builds available
        assert not ret
        ret = client.get_latest_build(42, all_passed=False)
        # returns build with all_passed=0 when all_passed is False
        assert ret == "1"
        fakerequest.return_value = {
            "build_results": [
                {"all_passed": 1, "build": "2"},
                {"all_passed": 1, "build": "3"},
                {"all_passed": 1, "build": "4"},
                {"all_passed": 0, "build": "5"},
                {"all_passed": 1, "build": "qq"},
                {"all_passed": 1, "build": "001"},
            ]
        }
        ret = client.get_latest_build(42)
        # returns latest passed build when all_passed flag set to True
        assert ret == "4"
        ret = client.get_latest_build(42, all_passed=False)
        # returns latest failed build when all_passed flag set to False
        assert ret == "5"
        ret = client.get_latest_build(42, sort_key=len)
        assert ret == "001"
