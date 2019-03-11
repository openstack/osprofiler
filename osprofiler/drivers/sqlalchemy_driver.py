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

from oslo_serialization import jsonutils

from osprofiler.drivers import base
from osprofiler import exc

LOG = logging.getLogger(__name__)


class SQLAlchemyDriver(base.Driver):
    def __init__(self, connection_str, project=None, service=None, host=None,
                 **kwargs):
        super(SQLAlchemyDriver, self).__init__(connection_str, project=project,
                                               service=service, host=host)

        try:
            from sqlalchemy import create_engine
            from sqlalchemy import Table, MetaData, Column
            from sqlalchemy import String, JSON, Integer
        except ImportError:
            LOG.exception("To use this command, install 'SQLAlchemy'")
        else:
            self._metadata = MetaData()
            self._data_table = Table(
                "data", self._metadata,
                Column("id", Integer, primary_key=True),
                # timestamp - date/time of the trace point
                Column("timestamp", String(26), index=True),
                # base_id - uuid common for all notifications related to
                # one trace
                Column("base_id", String(255), index=True),
                # parent_id - uuid of parent element in trace
                Column("parent_id", String(255), index=True),
                # trace_id - uuid of current element in trace
                Column("trace_id", String(255), index=True),
                Column("project", String(255), index=True),
                Column("host", String(255), index=True),
                Column("service", String(255), index=True),
                # name - trace point name
                Column("name", String(255), index=True),
                Column("data", JSON)
            )

        # we don't want to kill any service that does use osprofiler
        try:
            self._engine = create_engine(connection_str)
            self._conn = self._engine.connect()

            # FIXME(toabctl): Not the best idea to create the table on every
            # startup when using the sqlalchemy driver...
            self._metadata.create_all(self._engine, checkfirst=True)
        except Exception:
            LOG.exception("Failed to create engine/connection and setup "
                          "intial database tables")

    @classmethod
    def get_name(cls):
        return "sqlalchemy"

    def notify(self, info, context=None):
        """Write a notification the the database"""
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
            ins = self._data_table.insert().values(
                timestamp=timestamp,
                base_id=base_id,
                parent_id=parent_id,
                trace_id=trace_id,
                project=project,
                service=service,
                host=host,
                name=name,
                data=jsonutils.dumps(data)
            )
            self._conn.execute(ins)
        except Exception:
            LOG.exception("Can not store osprofiler tracepoint {} "
                          "(base_id {})".format(trace_id, base_id))

    def get_report(self, base_id):
        try:
            from sqlalchemy.sql import select
        except ImportError:
            raise exc.CommandError(
                "To use this command, you should install 'SQLAlchemy'")
        stmt = select([self._data_table]).where(
            self._data_table.c.base_id == base_id)
        results = self._conn.execute(stmt).fetchall()
        for n in results:
            timestamp = n["timestamp"]
            trace_id = n["trace_id"]
            parent_id = n["parent_id"]
            name = n["name"]
            project = n["project"]
            service = n["service"]
            host = n["host"]
            data = jsonutils.loads(n["data"])
            self._append_results(trace_id, parent_id, name, project, service,
                                 host, timestamp, data)
        return self._parse_results()
