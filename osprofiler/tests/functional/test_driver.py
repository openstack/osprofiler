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

import os
import tempfile

from oslo_config import cfg
from oslo_messaging import transport  # type: ignore[import-not-found]

from osprofiler.drivers import base
from osprofiler import initializer
from osprofiler import opts  # noqa
from osprofiler import profiler
from osprofiler.tests import test


CONF = cfg.CONF


@profiler.trace_cls("rpc", hide_args=True)
class Foo:
    def bar(self, x):
        return self.baz(x, x)

    def baz(self, x, y):
        return x * y


class DriverTestBase(test.FunctionalTestCase):
    SERVICE = "service"
    PROJECT = "project"

    @property
    def connection_string(self):
        raise NotImplementedError()

    def setUp(self):
        super().setUp()
        self.config_fixture.config(
            connection_string=self.connection_string,
            group='profiler',
            enabled=True,
            trace_sqlalchemy=False,
            hmac_keys="SECRET_KEY",
        )
        CONF.register_opts(transport._transport_opts)
        self.config_fixture.config(
            transport_url='rabbit://localhost:5672/',
        )

    def _assert_dict(self, info, **kwargs):
        self.assertLess(kwargs.items(), info.items())

    def _assert_child_dict(self, child, base_id, parent_id, name, fn_name):
        self.assertEqual(parent_id, child["parent_id"])

        exp_info = {
            "name": "rpc",
            "service": self.SERVICE,
            "project": self.PROJECT,
        }
        self._assert_dict(child["info"], **exp_info)

        raw_start = child["info"][f"meta.raw_payload.{name}-start"]
        self.assertEqual(fn_name, raw_start["info"]["function"]["name"])
        exp_raw = {
            "name": f"{name}-start",
            "service": self.SERVICE,
            "trace_id": child["trace_id"],
            "project": self.PROJECT,
            "base_id": base_id,
        }
        self._assert_dict(raw_start, **exp_raw)

        raw_stop = child["info"][f"meta.raw_payload.{name}-stop"]
        exp_raw["name"] = f"{name}-stop"
        self._assert_dict(raw_stop, **exp_raw)

    def _test_get_report(self):
        # initialize profiler notifier (the same way as in services)
        initializer.init_from_conf(
            CONF, {}, self.PROJECT, self.SERVICE, "host"
        )
        profiler.init("SECRET_KEY")

        # grab base_id
        p = profiler.get()
        assert p is not None  # noqa: S101
        base_id = p.get_base_id()

        # execute profiled code
        foo = Foo()
        foo.bar(1)

        # instantiate report engine (the same way as in osprofiler CLI)
        engine = base.get_driver(
            CONF.profiler.connection_string,
            project=self.PROJECT,
            service=self.SERVICE,
            host="host",
            conf=CONF,
        )

        # generate the report
        report = engine.get_report(base_id)

        # verify the report
        self.assertEqual("total", report["info"]["name"])
        self.assertEqual(2, report["stats"]["rpc"]["count"])
        self.assertEqual(1, len(report["children"]))

        cbar = report["children"][0]
        self._assert_child_dict(
            cbar,
            base_id,
            base_id,
            "rpc",
            "osprofiler.tests.functional.test_driver.Foo.bar",
        )

        self.assertEqual(1, len(cbar["children"]))
        cbaz = cbar["children"][0]
        self._assert_child_dict(
            cbaz,
            base_id,
            cbar["trace_id"],
            "rpc",
            "osprofiler.tests.functional.test_driver.Foo.baz",
        )

    def _test_list_traces(self):
        # initialize profiler notifier (the same way as in services)
        initializer.init_from_conf(
            CONF, {}, self.PROJECT, self.SERVICE, "host"
        )
        profiler.init("SECRET_KEY")

        # grab base_id
        p = profiler.get()
        assert p is not None  # noqa: S101
        base_id = p.get_base_id()

        # execute profiled code
        foo = Foo()
        foo.bar(1)

        # instantiate report engine (the same way as in osprofiler CLI)
        engine = base.get_driver(
            CONF.profiler.connection_string,
            project=self.PROJECT,
            service=self.SERVICE,
            host="host",
            conf=CONF,
        )

        # generate the report
        traces = engine.list_traces()

        # ensure trace with base_id is in the list of traces
        self.assertIn(base_id, [t["base_id"] for t in traces])


class MessagingDriverTestCase(DriverTestBase):
    @property
    def connection_string(self):
        return "messaging://"

    def test_get_report(self):
        super()._test_get_report()


class RedisDriverTestCase(DriverTestBase):
    @property
    def connection_string(self):
        return "redis://localhost:6379"

    def test_get_report(self):
        super()._test_get_report()

    def test_list_traces(self):
        super()._test_list_traces()


class SqliteDriverTestCase(DriverTestBase):
    def setUp(self):
        fd, self.db_file = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(os.remove, self.db_file)
        super().setUp()

    @property
    def connection_string(self):
        return f"sqlite:///{self.db_file}"

    def test_get_report(self):
        super()._test_get_report()

    def test_list_traces(self):
        super()._test_list_traces()
