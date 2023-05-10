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
from urllib import parse as parser

from oslo_config import cfg
from oslo_serialization import jsonutils

from osprofiler import _utils as utils
from osprofiler.drivers import base
from osprofiler import exc


class OTLP(base.Driver):
    def __init__(self, connection_str, project=None, service=None, host=None,
                 conf=cfg.CONF, **kwargs):
        """OTLP driver using OTLP exporters."""

        super(OTLP, self).__init__(connection_str, project=project,
                                   service=service, host=host,
                                   conf=conf, **kwargs)
        try:
            from opentelemetry import trace as trace_api

            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # noqa
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.trace import TracerProvider

            self.trace_api = trace_api
        except ImportError:
            raise exc.CommandError(
                "To use OSProfiler with OTLP exporters, "
                "please install `opentelemetry-sdk` and "
                "opentelemetry-exporter-otlp libraries. "
                "To install with pip:\n `pip install opentelemetry-sdk "
                "opentelemetry-exporter-otlp`.")

        service_name = self._get_service_name(conf, project, service)
        resource = Resource(attributes={
            "service.name": service_name
        })

        parsed_url = parser.urlparse(connection_str)
        # TODO("sahid"): We also want to handle https scheme?
        parsed_url = parsed_url._replace(scheme="http")

        self.trace_api.set_tracer_provider(
            TracerProvider(resource=resource))
        self.tracer = self.trace_api.get_tracer(__name__)

        exporter = OTLPSpanExporter("{}/v1/traces".format(
            parsed_url.geturl()))
        self.trace_api.get_tracer_provider().add_span_processor(
            BatchSpanProcessor(exporter))

        self.spans = collections.deque()

    def _get_service_name(self, conf, project, service):
        prefix = conf.profiler_otlp.service_name_prefix
        if prefix:
            return "{}-{}-{}".format(prefix, project, service)
        return "{}-{}".format(project, service)

    @classmethod
    def get_name(cls):
        return "otlp"

    def _kind(self, name):
        if "wsgi" in name:
            return self.trace_api.SpanKind.SERVER
        elif ("db" in name or "http" in name or "api" in name):
            return self.trace_api.SpanKind.CLIENT
        return self.trace_api.SpanKind.INTERNAL

    def _name(self, payload):
        info = payload["info"]
        if info.get("request"):
            return "WSGI_{}_{}".format(
                info["request"]["method"], info["request"]["path"])
        elif info.get("db"):
            return "SQL_{}".format(
                info["db"]["statement"].split(' ', 1)[0].upper())
        elif info.get("requests"):
            return "REQUESTS_{}_{}".format(
                info["requests"]["method"], info["requests"]["hostname"])
        return payload["name"].rstrip("-start")

    def notify(self, payload):
        if payload["name"].endswith("start"):
            parent = self.trace_api.SpanContext(
                trace_id=utils.uuid_to_int128(payload["base_id"]),
                span_id=utils.shorten_id(payload["parent_id"]),
                is_remote=False,
                trace_flags=self.trace_api.TraceFlags(
                    self.trace_api.TraceFlags.SAMPLED))

            ctx = self.trace_api.set_span_in_context(
                self.trace_api.NonRecordingSpan(parent))

            # OTLP Tracing span
            span = self.tracer.start_span(
                name=self._name(payload),
                kind=self._kind(payload['name']),
                attributes=self.create_span_tags(payload),
                context=ctx)

            span._context = self.trace_api.SpanContext(
                trace_id=span.context.trace_id,
                span_id=utils.shorten_id(payload["trace_id"]),
                is_remote=span.context.is_remote,
                trace_flags=span.context.trace_flags,
                trace_state=span.context.trace_state)

            self.spans.append(span)
        else:
            span = self.spans.pop()

            # Store result of db call and function call
            for call in ("db", "function"):
                if payload.get("info", {}).get(call):
                    span.set_attribute(
                        "result", payload["info"][call]["result"])
            # Store result of requests
            if payload.get("info", {}).get("requests"):
                span.set_attribute(
                    "status_code", payload["info"]["requests"]["status_code"])
            # Span error tag and log
            if payload["info"].get("etype"):
                span.set_attribute("error", True)
                span.add_event("log", {
                    "error.kind": payload["info"]["etype"],
                    "message": payload["info"]["message"]})
            span.end()

    def get_report(self, base_id):
        return self._parse_results()

    def list_traces(self, fields=None):
        return []

    def list_error_traces(self):
        return []

    def create_span_tags(self, payload):
        """Create tags an OpenTracing compatible span.

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
        elif info.get("requests"):
            # requests call
            tags["http.path"] = info["requests"]["path"]
            tags["http.query"] = info["requests"]["query"]
            tags["http.method"] = info["requests"]["method"]
            tags["http.scheme"] = info["requests"]["scheme"]
            tags["http.hostname"] = info["requests"]["hostname"]
            tags["http.port"] = info["requests"]["port"]
        elif info.get("function"):
            # RPC, function calls
            if "args" in info["function"]:
                tags["args"] = info["function"]["args"]
            if "kwargs" in info["function"]:
                tags["kwargs"] = info["function"]["kwargs"]
            tags["name"] = info["function"]["name"]

        return tags
