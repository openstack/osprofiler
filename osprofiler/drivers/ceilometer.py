# Copyright 2016 Mirantis Inc.
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

from osprofiler.drivers import base
from osprofiler import exc


class Ceilometer(base.Driver):
    def __init__(self, connection_str, **kwargs):
        """Driver receiving profiled information from ceilometer."""
        super(Ceilometer, self).__init__(connection_str)
        try:
            import ceilometerclient.client
        except ImportError:
            raise exc.CommandError(
                "To use this command, you should install "
                "'ceilometerclient' manually. Use command:\n "
                "'pip install python-ceilometerclient'.")

        try:
            self.client = ceilometerclient.client.get_client(
                kwargs["ceilometer_api_version"], **kwargs)
        except Exception as e:
            if hasattr(e, "http_status") and e.http_status == 401:
                msg = "Invalid OpenStack Identity credentials."
            else:
                msg = ("Something has gone wrong. See ceilometer logs "
                       "for more details")
            raise exc.CommandError(msg)

    @classmethod
    def get_name(cls):
        return "ceilometer"

    def get_report(self, base_id):
        """Retrieves and parses notification from ceilometer.

        :param base_id: Base id of trace elements.
        """

        _filter = [{"field": "base_id", "op": "eq", "value": base_id}]

        # limit is hardcoded in this code state. Later that will be changed via
        # connection string usage
        notifications = [n.to_dict()
                         for n in self.client.events.list(_filter,
                                                          limit=100000)]

        for n in notifications:
            traits = n["traits"]

            def find_field(f_name):
                return [t["value"] for t in traits if t["name"] == f_name][0]

            trace_id = find_field("trace_id")
            parent_id = find_field("parent_id")
            name = find_field("name")
            project = find_field("project")
            service = find_field("service")
            host = find_field("host")
            timestamp = find_field("timestamp")

            payload = n.get("raw", {}).get("payload", {})

            self._append_results(trace_id, parent_id, name, project, service,
                                 host, timestamp, payload)

        return self._parse_results()
