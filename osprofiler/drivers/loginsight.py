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

"""
Classes to use VMware vRealize Log Insight as the trace data store.
"""

import json
import logging as log

import netaddr
from oslo_concurrency.lockutils import synchronized
import requests
import six.moves.urllib.parse as urlparse

from osprofiler.drivers import base
from osprofiler import exc

LOG = log.getLogger(__name__)


class LogInsightDriver(base.Driver):
    """Driver for storing trace data in VMware vRealize Log Insight.

    The driver uses Log Insight ingest service to store trace data and uses
    the query service to retrieve it. The minimum required Log Insight version
    is 3.3.

    The connection string to initialize the driver should be of the format:
        loginsight://<username>:<password>@<loginsight-host>

    If the username or password contains the character ':' or '@', it must be
    escaped using URL encoding. For example, the connection string to connect
    to Log Insight server at 10.1.2.3 using username "osprofiler" and password
    "p@ssword" is:
        loginsight://osprofiler:p%40ssword@10.1.2.3
    """
    def __init__(
            self, connection_str, project=None, service=None, host=None,
            **kwargs):
        super(LogInsightDriver, self).__init__(connection_str,
                                               project=project,
                                               service=service,
                                               host=host)

        parsed_connection = urlparse.urlparse(connection_str)
        try:
            creds, host = parsed_connection.netloc.split("@")
            username, password = creds.split(":")
        except ValueError:
            raise ValueError("Connection string format is: loginsight://"
                             "<username>:<password>@<loginsight-host>. If the "
                             "username or password contains the character '@' "
                             "or ':', it must be escaped using URL encoding.")

        username = urlparse.unquote(username)
        password = urlparse.unquote(password)
        self._client = LogInsightClient(host, username, password)

        self._client.login()

    @classmethod
    def get_name(cls):
        return "loginsight"

    def notify(self, info):
        """Send trace to Log Insight server."""

        trace = info.copy()
        trace["project"] = self.project
        trace["service"] = self.service

        event = {"text": "OSProfiler trace"}

        def _create_field(name, content):
            return {"name": name, "content": content}

        event["fields"] = [_create_field("base_id", trace["base_id"]),
                           _create_field("trace_id", trace["trace_id"]),
                           _create_field("project", trace["project"]),
                           _create_field("service", trace["service"]),
                           _create_field("name", trace["name"]),
                           _create_field("trace", json.dumps(trace))]

        self._client.send_event(event)

    def get_report(self, base_id):
        """Retrieves and parses trace data from Log Insight.

        :param base_id: Trace base ID
        """
        response = self._client.query_events({"base_id": base_id})

        if "events" in response:
            for event in response["events"]:
                if "fields" not in event:
                    continue

                for field in event["fields"]:
                    if field["name"] == "trace":
                        trace = json.loads(field["content"])
                        trace_id = trace["trace_id"]
                        parent_id = trace["parent_id"]
                        name = trace["name"]
                        project = trace["project"]
                        service = trace["service"]
                        host = trace["info"]["host"]
                        timestamp = trace["timestamp"]

                        self._append_results(
                            trace_id, parent_id, name, project, service, host,
                            timestamp, trace)
                        break

        return self._parse_results()


class LogInsightClient(object):
    """A minimal Log Insight client."""

    LI_OSPROFILER_AGENT_ID = "F52D775B-6017-4787-8C8A-F21AE0AEC057"

    # API paths
    SESSIONS_PATH = "api/v1/sessions"
    CURRENT_SESSIONS_PATH = "api/v1/sessions/current"
    EVENTS_INGEST_PATH = "api/v1/events/ingest/%s" % LI_OSPROFILER_AGENT_ID
    QUERY_EVENTS_BASE_PATH = "api/v1/events"

    def __init__(self, host, username, password, api_port=9000,
                 api_ssl_port=9543, query_timeout=60000):
        self._host = host
        self._username = username
        self._password = password
        self._api_port = api_port
        self._api_ssl_port = api_ssl_port
        self._query_timeout = query_timeout
        self._session = requests.Session()
        self._session_id = None

    def _build_base_url(self, scheme):
        proto_str = "%s://" % scheme
        host_str = ("[%s]" % self._host if netaddr.valid_ipv6(self._host)
                    else self._host)
        port_str = ":%d" % (self._api_ssl_port if scheme == "https"
                            else self._api_port)
        return proto_str + host_str + port_str

    def _check_response(self, resp):
        if resp.status_code == 440:
            raise exc.LogInsightLoginTimeout()

        if not resp.ok:
            msg = "n/a"
            if resp.text:
                try:
                    body = json.loads(resp.text)
                    msg = body.get("errorMessage", msg)
                except ValueError:
                    pass
            else:
                msg = resp.reason
            raise exc.LogInsightAPIError(msg)

    def _send_request(
            self, method, scheme, path, headers=None, body=None, params=None):
        url = "%s/%s" % (self._build_base_url(scheme), path)

        headers = headers or {}
        headers["content-type"] = "application/json"
        body = body or {}
        params = params or {}

        req = requests.Request(
            method, url, headers=headers, data=json.dumps(body), params=params)
        req = req.prepare()
        resp = self._session.send(req, verify=False)

        self._check_response(resp)
        return resp.json()

    def _get_auth_header(self):
        return {"X-LI-Session-Id": self._session_id}

    def _trunc_session_id(self):
        if self._session_id:
            return self._session_id[-5:]

    def _is_current_session_active(self):
        try:
            self._send_request("get",
                               "https",
                               self.CURRENT_SESSIONS_PATH,
                               headers=self._get_auth_header())
            LOG.debug("Current session %s is active.",
                      self._trunc_session_id())
            return True
        except (exc.LogInsightLoginTimeout, exc.LogInsightAPIError):
            LOG.debug("Current session %s is not active.",
                      self._trunc_session_id())
            return False

    @synchronized("li_login_lock")
    def login(self):
        # Another thread might have created the session while the current
        # thread was waiting for the lock.
        if self._session_id and self._is_current_session_active():
            return

        LOG.info("Logging into Log Insight server: %s.", self._host)
        resp = self._send_request("post",
                                  "https",
                                  self.SESSIONS_PATH,
                                  body={"username": self._username,
                                        "password": self._password})

        self._session_id = resp["sessionId"]
        LOG.debug("Established session %s.", self._trunc_session_id())

    def send_event(self, event):
        events = {"events": [event]}
        self._send_request("post",
                           "http",
                           self.EVENTS_INGEST_PATH,
                           body=events)

    def query_events(self, params):
        # Assumes that the keys and values in the params are strings and
        # the operator is "CONTAINS".
        constraints = []
        for field, value in params.items():
            constraints.append("%s/CONTAINS+%s" % (field, value))
        constraints.append("timestamp/GT+0")

        path = "%s/%s" % (self.QUERY_EVENTS_BASE_PATH, "/".join(constraints))

        def _query_events():
            return self._send_request("get",
                                      "https",
                                      path,
                                      headers=self._get_auth_header(),
                                      params={"limit": 20000,
                                              "timeout": self._query_timeout})
        try:
            resp = _query_events()
        except exc.LogInsightLoginTimeout:
            # Login again and re-try.
            LOG.debug("Current session timed out.")
            self.login()
            resp = _query_events()

        return resp
