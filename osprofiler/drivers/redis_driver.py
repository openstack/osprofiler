# Copyright 2016 Mirantis Inc.
# Copyright 2016 IBM Corporation.
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

from collections.abc import Generator
from typing import Any, cast
from urllib import parse as parser

from debtcollector import removals
from oslo_config import cfg
from oslo_serialization import jsonutils

from osprofiler.drivers import base
from osprofiler import exc


class Redis(base.Driver):
    @removals.removed_kwarg(
        "db",
        message="'db' parameter is deprecated "
        "and will be removed in future. "
        "Please specify 'db' in "
        "'connection_string' instead.",
    )
    def __init__(
        self,
        connection_str: str,
        db: int = 0,
        project: str | None = None,
        service: str | None = None,
        host: str | None = None,
        conf: cfg.ConfigOpts = cfg.CONF,
        **kwargs: Any,
    ) -> None:
        """Redis driver for OSProfiler."""

        super().__init__(
            connection_str,
            project=project,
            service=service,
            host=host,
            conf=conf,
            **kwargs,
        )
        try:
            from redis import Redis as _Redis
        except ImportError:
            raise exc.CommandError(
                "To use OSProfiler with Redis driver, "
                "please install `redis` library. "
                "To install with pip:\n `pip install redis`."
            )

        # only connection over network is supported with schema
        # redis://[:password]@host[:port][/db]
        self.db = _Redis.from_url(self.connection_str)
        self.namespace_opt = "osprofiler_opt:"
        self.namespace = "osprofiler:"  # legacy
        self.namespace_error = "osprofiler_error:"

    @classmethod
    def get_name(cls) -> str:
        return "redis"

    def notify(self, info: dict[str, Any], **kwargs: Any) -> None:
        """Send notifications to Redis.

        :param info:  Contains information about trace element.
                      In payload dict there are always 3 ids:
                      "base_id" - uuid that is common for all notifications
                      related to one trace. Used to simplify retrieving of all
                      trace elements from Redis.
                      "parent_id" - uuid of parent element in trace
                      "trace_id" - uuid of current element in trace
                      With parent_id and trace_id it's quite simple to build
                      tree of trace elements, which simplify analyze of trace.
        """
        data = info.copy()
        data["project"] = self.project
        data["service"] = self.service
        key = self.namespace_opt + data["base_id"]
        self.db.lpush(key, jsonutils.dumps(data))

        if (
            self.filter_error_trace
            and data.get("info", {}).get("etype") is not None
        ):
            self.notify_error_trace(data)

    def notify_error_trace(self, data: dict[str, Any]) -> None:
        """Store base_id and timestamp of error trace to a separate key."""
        key = self.namespace_error + data["base_id"]
        value = jsonutils.dumps(
            {"base_id": data["base_id"], "timestamp": data["timestamp"]}
        )
        self.db.set(key, value)

    def list_traces(
        self, fields: set[str] | None = None
    ) -> list[dict[str, Any]]:
        """Query all traces from the storage.

        :param fields: Set of trace fields to return. Defaults to 'base_id'
                       and 'timestamp'
        :returns: List of traces, where each trace is a dictionary containing
                  at least `base_id` and `timestamp`.
        """
        fields = set(fields or self.default_trace_fields)

        # first get legacy events
        result = self._list_traces_legacy(fields)

        # with optimized schema trace events are stored in a list
        ids = self.db.scan_iter(match=self.namespace_opt + "*")
        for i in ids:
            # for each trace query the first event to have a timestamp
            raw = cast(bytes | None, self.db.lindex(i, 1))
            if raw is None:
                continue
            first_event = jsonutils.loads(raw)
            result.append(
                {
                    key: value
                    for key, value in first_event.items()
                    if key in fields
                }
            )
        return result

    def _list_traces_legacy(self, fields: set[str]) -> list[dict[str, Any]]:
        # With current schema every event is stored under its own unique key
        # To query all traces we first need to get all keys, then
        # get all events, sort them and pick up only the first one
        ids = self.db.scan_iter(match=self.namespace + "*")
        traces = [
            jsonutils.loads(raw)
            for i in ids
            if (raw := cast(bytes | None, self.db.get(i))) is not None
        ]
        traces.sort(key=lambda x: x["timestamp"])
        seen_ids: set[str] = set()
        result: list[dict[str, Any]] = []
        for trace in traces:
            if trace["base_id"] not in seen_ids:
                seen_ids.add(trace["base_id"])
                result.append(
                    {
                        key: value
                        for key, value in trace.items()
                        if key in fields
                    }
                )
        return result

    def list_error_traces(self) -> list[dict[str, Any]]:
        """Returns all traces that have error/exception."""
        ids = self.db.scan_iter(match=self.namespace_error + "*")
        traces = [
            jsonutils.loads(raw)
            for i in ids
            if (raw := cast(bytes | None, self.db.get(i))) is not None
        ]
        traces.sort(key=lambda x: x["timestamp"])
        seen_ids: set[str] = set()
        result: list[dict[str, Any]] = []
        for trace in traces:
            if trace["base_id"] not in seen_ids:
                seen_ids.add(trace["base_id"])
                result.append(trace)

        return result

    def get_report(self, base_id: str) -> dict[str, Any]:
        """Retrieves and parses notification from Redis.

        :param base_id: Base id of trace elements.
        """

        def iterate_events() -> Generator[bytes, None, None]:
            for key in self.db.scan_iter(
                match=self.namespace + base_id + "*"
            ):  # legacy
                data = cast(bytes | None, self.db.get(key))
                if data is not None:
                    yield data

            yield from cast(
                list[bytes],
                self.db.lrange(self.namespace_opt + base_id, 0, -1),
            )

        for data in iterate_events():
            n = jsonutils.loads(data)
            trace_id = n["trace_id"]
            parent_id = n["parent_id"]
            name = n["name"]
            project = n["project"]
            service = n["service"]
            host = n["info"]["host"]
            timestamp = n["timestamp"]

            self._append_results(
                trace_id, parent_id, name, project, service, host, timestamp, n
            )

        return self._parse_results()


class RedisSentinel(Redis, base.Driver):
    @removals.removed_kwarg(
        "db",
        message="'db' parameter is deprecated "
        "and will be removed in future. "
        "Please specify 'db' in "
        "'connection_string' instead.",
    )
    def __init__(
        self,
        connection_str: str,
        db: int = 0,
        project: str | None = None,
        service: str | None = None,
        host: str | None = None,
        conf: cfg.ConfigOpts = cfg.CONF,
        **kwargs: Any,
    ) -> None:
        """Redis driver for OSProfiler."""

        super().__init__(
            connection_str,
            project=project,
            service=service,
            host=host,
            conf=conf,
            **kwargs,
        )
        try:
            from redis.sentinel import Sentinel
        except ImportError:
            raise exc.CommandError(
                "To use this command, you should install "
                "'redis' manually. Use command:\n "
                "'pip install redis'."
            )

        self.conf = conf
        socket_timeout = self.conf.profiler.socket_timeout
        parsed_url = parser.urlparse(self.connection_str)
        sentinel = Sentinel(  # type: ignore[no-untyped-call]
            [(parsed_url.hostname, int(parsed_url.port))],  # type: ignore[arg-type]
            password=parsed_url.password,
            socket_timeout=socket_timeout,
        )
        self.db = sentinel.master_for(  # type: ignore[no-untyped-call]
            self.conf.profiler.sentinel_service_name,
            socket_timeout=socket_timeout,
        )

    @classmethod
    def get_name(cls) -> str:
        return "redissentinel"
