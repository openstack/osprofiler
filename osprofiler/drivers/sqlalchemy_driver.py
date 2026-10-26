# Copyright 2019 SUSE Linux GmbH
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

import logging
from typing import Any

from oslo_serialization import jsonutils

from osprofiler.drivers import base
from osprofiler import exc

LOG = logging.getLogger(__name__)


class SQLAlchemyDriver(base.Driver):
    def __init__(
        self,
        connection_str: str,
        project: str | None = None,
        service: str | None = None,
        host: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            connection_str, project=project, service=service, host=host
        )

        try:
            from osprofiler.drivers.sqlalchemy.models import Base
            from sqlalchemy import create_engine
        except ImportError:
            raise exc.CommandError("SQLAlchemy is not found")

        # we don't want to kill any service that does use osprofiler
        try:
            self._engine = create_engine(connection_str)

            # FIXME(toabctl): Not the best idea to create the table on every
            # startup when using the sqlalchemy driver...
            Base.metadata.create_all(self._engine)
        except Exception:
            LOG.exception(
                "Failed to create engine/connection and setup "
                "intial database tables"
            )
            raise

    @classmethod
    def get_name(cls) -> str:
        return "sqlalchemy"

    def notify(
        self, info: dict[str, Any], context: Any = None, **kwargs: Any
    ) -> None:
        """Write a notification the the database"""
        from osprofiler.drivers.sqlalchemy.models import Data
        from sqlalchemy.orm import Session

        data = info.copy()
        base_id = data.pop("base_id", None)
        timestamp = data.pop("timestamp", None)
        parent_id = data.pop("parent_id", None)
        trace_id = data.pop("trace_id", None)
        project = data.pop("project", self.project)
        host = data.pop("host", self.host)
        service = data.pop("service", self.service)
        name = data.pop("name", None)

        try:
            with Session(self._engine) as session:
                new_data = Data(
                    timestamp=timestamp,
                    base_id=base_id,
                    parent_id=parent_id,
                    trace_id=trace_id,
                    project=project,
                    service=service,
                    host=host,
                    name=name,
                    data=jsonutils.dumps(data),
                )
                session.add(new_data)
                session.commit()
        except Exception:
            LOG.exception(
                "Can not store osprofiler tracepoint %s (base id %s)",
                trace_id,
                base_id,
            )

    def list_traces(
        self, fields: set[str] | None = None
    ) -> list[dict[str, Any]]:
        from osprofiler.drivers.sqlalchemy.models import Data
        from sqlalchemy.orm import Session

        fields = set(fields or self.default_trace_fields)
        seen_ids: set[str] = set()
        result: list[dict[str, Any]] = []

        with Session(self._engine) as session:
            traces = session.query(Data).all()

            for trace in traces:
                if trace.base_id not in seen_ids:
                    seen_ids.add(trace.base_id)
                    result.append({key: getattr(trace, key) for key in fields})
        return result

    def get_report(self, base_id: str) -> dict[str, Any]:
        from osprofiler.drivers.sqlalchemy.models import Data
        from sqlalchemy.orm import Session

        with Session(self._engine) as session:
            traces = session.query(Data).filter(Data.base_id == base_id).all()
            for trace in traces:
                self._append_results(
                    trace.trace_id,
                    trace.parent_id,
                    trace.name,
                    trace.project,
                    trace.service,
                    trace.host,
                    trace.timestamp,
                    jsonutils.loads(trace.data),
                )
        return self._parse_results()
