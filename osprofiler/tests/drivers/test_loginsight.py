# Copyright (c) 2016 VMware, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json

import ddt
import mock

from osprofiler.drivers import loginsight
from osprofiler import exc
from osprofiler.tests import test


@ddt.ddt
class LogInsightDriverTestCase(test.TestCase):

    BASE_ID = "8d28af1e-acc0-498c-9890-6908e33eff5f"

    def setUp(self):
        super(LogInsightDriverTestCase, self).setUp()
        self._client = mock.Mock(spec=loginsight.LogInsightClient)
        self._project = "cinder"
        self._service = "osapi_volume"
        self._host = "ubuntu"
        with mock.patch.object(loginsight, "LogInsightClient",
                               return_value=self._client):
            self._driver = loginsight.LogInsightDriver(
                "loginsight://username:password@host",
                project=self._project,
                service=self._service,
                host=self._host)

    @mock.patch.object(loginsight, "LogInsightClient")
    def test_init(self, client_class):
        client = mock.Mock()
        client_class.return_value = client

        loginsight.LogInsightDriver("loginsight://username:password@host")
        client_class.assert_called_once_with("host", "username", "password")
        client.login.assert_called_once_with()

    @ddt.data("loginsight://username@host",
              "loginsight://username:p@ssword@host",
              "loginsight://us:rname:password@host")
    def test_init_with_invalid_connection_string(self, conn_str):
        self.assertRaises(ValueError, loginsight.LogInsightDriver, conn_str)

    @mock.patch.object(loginsight, "LogInsightClient")
    def test_init_with_special_chars_in_conn_str(self, client_class):
        client = mock.Mock()
        client_class.return_value = client

        loginsight.LogInsightDriver("loginsight://username:p%40ssword@host")
        client_class.assert_called_once_with("host", "username", "p@ssword")
        client.login.assert_called_once_with()

    def test_get_name(self):
        self.assertEqual("loginsight", self._driver.get_name())

    def _create_trace(self,
                      name,
                      timestamp,
                      parent_id="8d28af1e-acc0-498c-9890-6908e33eff5f",
                      base_id=BASE_ID,
                      trace_id="e465db5c-9672-45a1-b90b-da918f30aef6"):
        return {"parent_id": parent_id,
                "name": name,
                "base_id": base_id,
                "trace_id": trace_id,
                "timestamp": timestamp,
                "info": {"host": self._host}}

    def _create_start_trace(self):
        return self._create_trace("wsgi-start", "2016-10-04t11:50:21.902303")

    def _create_stop_trace(self):
        return self._create_trace("wsgi-stop", "2016-10-04t11:50:30.123456")

    @mock.patch("json.dumps")
    def test_notify(self, dumps):
        json_str = mock.sentinel.json_str
        dumps.return_value = json_str

        trace = self._create_stop_trace()
        self._driver.notify(trace)

        trace["project"] = self._project
        trace["service"] = self._service
        exp_event = {"text": "OSProfiler trace",
                     "fields": [{"name": "base_id",
                                 "content": trace["base_id"]},
                                {"name": "trace_id",
                                 "content": trace["trace_id"]},
                                {"name": "project",
                                 "content": trace["project"]},
                                {"name": "service",
                                 "content": trace["service"]},
                                {"name": "name",
                                 "content": trace["name"]},
                                {"name": "trace",
                                 "content": json_str}]
                     }
        self._client.send_event.assert_called_once_with(exp_event)

    @mock.patch.object(loginsight.LogInsightDriver, "_append_results")
    @mock.patch.object(loginsight.LogInsightDriver, "_parse_results")
    def test_get_report(self, parse_results, append_results):
        start_trace = self._create_start_trace()
        start_trace["project"] = self._project
        start_trace["service"] = self._service

        stop_trace = self._create_stop_trace()
        stop_trace["project"] = self._project
        stop_trace["service"] = self._service

        resp = {"events": [{"text": "OSProfiler trace",
                            "fields": [{"name": "trace",
                                        "content": json.dumps(start_trace)
                                        }
                                       ]
                            },
                           {"text": "OSProfiler trace",
                            "fields": [{"name": "trace",
                                        "content": json.dumps(stop_trace)
                                        }
                                       ]
                            }
                           ]
                }
        self._client.query_events = mock.Mock(return_value=resp)

        self._driver.get_report(self.BASE_ID)
        self._client.query_events.assert_called_once_with({"base_id":
                                                           self.BASE_ID})
        append_results.assert_has_calls(
            [mock.call(start_trace["trace_id"], start_trace["parent_id"],
                       start_trace["name"], start_trace["project"],
                       start_trace["service"], start_trace["info"]["host"],
                       start_trace["timestamp"], start_trace),
             mock.call(stop_trace["trace_id"], stop_trace["parent_id"],
                       stop_trace["name"], stop_trace["project"],
                       stop_trace["service"], stop_trace["info"]["host"],
                       stop_trace["timestamp"], stop_trace)
             ])
        parse_results.assert_called_once_with()


class LogInsightClientTestCase(test.TestCase):

    def setUp(self):
        super(LogInsightClientTestCase, self).setUp()
        self._host = "localhost"
        self._username = "username"
        self._password = "password"
        self._client = loginsight.LogInsightClient(
            self._host, self._username, self._password)
        self._client._session_id = "4ff800d1-3175-4b49-9209-39714ea56416"

    def test_check_response_login_timeout(self):
        resp = mock.Mock(status_code=440)
        self.assertRaises(
            exc.LogInsightLoginTimeout, self._client._check_response, resp)

    def test_check_response_api_error(self):
        resp = mock.Mock(status_code=401, ok=False)
        resp.text = json.dumps(
            {"errorMessage": "Invalid username or password.",
             "errorCode": "FIELD_ERROR"})
        e = self.assertRaises(
            exc.LogInsightAPIError, self._client._check_response, resp)
        self.assertEqual("Invalid username or password.", str(e))

    @mock.patch("requests.Request")
    @mock.patch("json.dumps")
    @mock.patch.object(loginsight.LogInsightClient, "_check_response")
    def test_send_request(self, check_resp, json_dumps, request_class):
        req = mock.Mock()
        request_class.return_value = req
        prep_req = mock.sentinel.prep_req
        req.prepare = mock.Mock(return_value=prep_req)

        data = mock.sentinel.data
        json_dumps.return_value = data

        self._client._session = mock.Mock()
        resp = mock.Mock()
        self._client._session.send = mock.Mock(return_value=resp)
        resp_json = mock.sentinel.resp_json
        resp.json = mock.Mock(return_value=resp_json)

        header = {"X-LI-Session-Id": "foo"}
        body = mock.sentinel.body
        params = mock.sentinel.params
        ret = self._client._send_request(
            "get", "https", "api/v1/events", header, body, params)

        self.assertEqual(resp_json, ret)
        exp_headers = {"X-LI-Session-Id": "foo",
                       "content-type": "application/json"}
        request_class.assert_called_once_with(
            "get", "https://localhost:9543/api/v1/events", headers=exp_headers,
            data=data, params=mock.sentinel.params)
        self._client._session.send.assert_called_once_with(prep_req,
                                                           verify=False)
        check_resp.assert_called_once_with(resp)

    @mock.patch.object(loginsight.LogInsightClient, "_send_request")
    def test_is_current_session_active_with_active_session(self, send_request):
        self.assertTrue(self._client._is_current_session_active())
        exp_header = {"X-LI-Session-Id": self._client._session_id}
        send_request.assert_called_once_with(
            "get", "https", "api/v1/sessions/current", headers=exp_header)

    @mock.patch.object(loginsight.LogInsightClient, "_send_request")
    def test_is_current_session_active_with_expired_session(self,
                                                            send_request):
        send_request.side_effect = exc.LogInsightLoginTimeout

        self.assertFalse(self._client._is_current_session_active())
        send_request.assert_called_once_with(
            "get", "https", "api/v1/sessions/current",
            headers={"X-LI-Session-Id": self._client._session_id})

    @mock.patch.object(loginsight.LogInsightClient,
                       "_is_current_session_active", return_value=True)
    @mock.patch.object(loginsight.LogInsightClient, "_send_request")
    def test_login_with_current_session_active(self, send_request,
                                               is_current_session_active):
        self._client.login()
        is_current_session_active.assert_called_once_with()
        send_request.assert_not_called()

    @mock.patch.object(loginsight.LogInsightClient,
                       "_is_current_session_active", return_value=False)
    @mock.patch.object(loginsight.LogInsightClient, "_send_request")
    def test_login(self, send_request, is_current_session_active):
        new_session_id = "569a80aa-be5c-49e5-82c1-bb62392d2667"
        resp = {"sessionId": new_session_id}
        send_request.return_value = resp

        self._client.login()
        is_current_session_active.assert_called_once_with()
        exp_body = {"username": self._username, "password": self._password}
        send_request.assert_called_once_with(
            "post", "https", "api/v1/sessions", body=exp_body)
        self.assertEqual(new_session_id, self._client._session_id)

    @mock.patch.object(loginsight.LogInsightClient, "_send_request")
    def test_send_event(self, send_request):
        event = mock.sentinel.event
        self._client.send_event(event)

        exp_body = {"events": [event]}
        exp_path = ("api/v1/events/ingest/%s" %
                    self._client.LI_OSPROFILER_AGENT_ID)
        send_request.assert_called_once_with(
            "post", "http", exp_path, body=exp_body)

    @mock.patch.object(loginsight.LogInsightClient, "_send_request")
    def test_query_events(self, send_request):
        resp = mock.sentinel.response
        send_request.return_value = resp

        self.assertEqual(resp, self._client.query_events({"foo": "bar"}))
        exp_header = {"X-LI-Session-Id": self._client._session_id}
        exp_params = {"limit": 20000, "timeout": self._client._query_timeout}
        send_request.assert_called_once_with(
            "get", "https", "api/v1/events/foo/CONTAINS+bar/timestamp/GT+0",
            headers=exp_header, params=exp_params)

    @mock.patch.object(loginsight.LogInsightClient, "_send_request")
    @mock.patch.object(loginsight.LogInsightClient, "login")
    def test_query_events_with_session_expiry(self, login, send_request):
        resp = mock.sentinel.response
        send_request.side_effect = [exc.LogInsightLoginTimeout, resp]

        self.assertEqual(resp, self._client.query_events({"foo": "bar"}))
        login.assert_called_once_with()
        exp_header = {"X-LI-Session-Id": self._client._session_id}
        exp_params = {"limit": 20000, "timeout": self._client._query_timeout}
        exp_send_request_call = mock.call(
            "get", "https", "api/v1/events/foo/CONTAINS+bar/timestamp/GT+0",
            headers=exp_header, params=exp_params)
        send_request.assert_has_calls([exp_send_request_call]*2)
