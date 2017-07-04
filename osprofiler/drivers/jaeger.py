# Copyright 2018 Fujitsu Ltd.
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

import collections
import datetime
import time

from oslo_config import cfg
from oslo_serialization import jsonutils
import six.moves.urllib.parse as parser

from osprofiler import _utils as utils
from osprofiler.drivers import base
from osprofiler import exc


class Jaeger(base.Driver):
    def __init__(self, connection_str, project=None, service=None, host=None,
                 conf=cfg.CONF, **kwargs):
        """Jaeger driver for OSProfiler."""

        super(Jaeger, self).__init__(connection_str, project=project,
                                     service=service, host=host,
                                     conf=conf, **kwargs)
        try:
            import jaeger_client
            self.jaeger_client = jaeger_client
        except ImportError:
            raise exc.CommandError(
                "To use OSProfiler with Uber Jaeger tracer, "
                "you have to install `jaeger-client` manually. "
                "Install with pip:\n `pip install jaeger-client`."
            )

        parsed_url = parser.urlparse(connection_str)
        cfg = {
            "local_agent": {
                "reporting_host": parsed_url.hostname,
                "reporting_port": parsed_url.port,
            }
        }

        # Initialize tracer for each profiler
        service_name = "{}-{}".format(project, service)
        config = jaeger_client.Config(cfg, service_name=service_name)
        self.tracer = config.initialize_tracer()

        self.spans = collections.deque()

    @classmethod
    def get_name(cls):
        return "jaeger"

    def notify(self, payload):
        if payload["name"].endswith("start"):
            timestamp = datetime.datetime.strptime(payload["timestamp"],
                                                   "%Y-%m-%dT%H:%M:%S.%f")
            epoch = datetime.datetime.utcfromtimestamp(0)
            start_time = (timestamp - epoch).total_seconds()

            # Create parent span
            child_of = self.jaeger_client.SpanContext(
                trace_id=utils.shorten_id(payload["base_id"]),
                span_id=utils.shorten_id(payload["parent_id"]),
                parent_id=None,
                flags=self.jaeger_client.span.SAMPLED_FLAG
            )

            # Create Jaeger Tracing span
            span = self.tracer.start_span(
                operation_name=payload["name"].rstrip("-start"),
                child_of=child_of,
                tags=self.create_span_tags(payload),
                start_time=start_time
            )

            # Replace Jaeger Tracing span_id (random id) to OSProfiler span_id
            span.context.span_id = utils.shorten_id(payload["trace_id"])
            self.spans.append(span)
        else:
            span = self.spans.pop()

            # Store result of db call and function call
            for call in ("db", "function"):
                if payload.get("info", {}).get(call) is not None:
                    span.set_tag("result", payload["info"][call]["result"])

            # Span error tag and log
            if payload["info"].get("etype") is not None:
                span.set_tag("error", True)
                span.log_kv({"error.kind": payload["info"]["etype"]})
                span.log_kv({"message": payload["info"]["message"]})

            span.finish(finish_time=time.time())

    def get_report(self, base_id):
        """Please use Jaeger Tracing UI for this task."""
        return self._parse_results()

    def list_traces(self, fields=None):
        """Please use Jaeger Tracing UI for this task."""
        return []

    def list_error_traces(self):
        """Please use Jaeger Tracing UI for this task."""
        return []

    def create_span_tags(self, payload):
        """Create tags for OpenTracing span.

        :param info: Information from OSProfiler trace.
        :returns tags: A dictionary contains standard tags
                       from OpenTracing sematic conventions,
                       and some other custom tags related to http, db calls.
        """
        tags = {}
        info = payload["info"]

        if info.get("db"):
            # DB calls
            tags["db.statement"] = info["db"]["statement"]
            tags["db.params"] = jsonutils.dumps(info["db"]["params"])
        elif info.get("request"):
            # WSGI call
            tags["http.path"] = info["request"]["path"]
            tags["http.query"] = info["request"]["query"]
            tags["http.method"] = info["request"]["method"]
            tags["http.scheme"] = info["request"]["scheme"]
        elif info.get("function"):
            # RPC, function calls
            tags["args"] = info["function"]["args"]
            tags["kwargs"] = info["function"]["kwargs"]
            tags["name"] = info["function"]["name"]

        return tags
