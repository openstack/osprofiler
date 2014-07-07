# Copyright 2014 Mirantis Inc.
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
import mock

from osprofiler import profiler

from tests import test


class ProfilerGlobMethodsTestCase(test.TestCase):

    def test_get_profiler_not_inited(self):
        profiler._clean()
        self.assertIsNone(profiler.get())

    def test_get_profiler_and_init(self):
        p = profiler.init("secret", base_id="1", parent_id="2")
        self.assertEqual(profiler.get(), p)

        self.assertEqual(p.get_base_id(), "1")
        # NOTE(boris-42): until we make first start we don't have
        self.assertEqual(p.get_id(), "2")

    def test_start_not_inited(self):
        profiler._clean()
        profiler.start("name")

    def test_start(self):
        p = profiler.init("secret", base_id="1", parent_id="2")
        p.start = mock.MagicMock()
        profiler.start("name", info="info")
        p.start.assert_called_once_with("name", info="info")

    def test_stop_not_inited(self):
        profiler._clean()
        profiler.stop()

    def test_stop(self):
        p = profiler.init("secret", base_id="1", parent_id="2")
        p.stop = mock.MagicMock()
        profiler.stop(info="info")
        p.stop.assert_called_once_with(info="info")


class ProfilerTestCase(test.TestCase):

    def test_profiler_get_base_id(self):
        prof = profiler._Profiler("secret", base_id="1", parent_id="2")
        self.assertEqual(prof.get_base_id(), "1")

    @mock.patch("osprofiler.profiler.uuid.uuid4")
    def test_profiler_get_parent_id(self, mock_uuid4):
        mock_uuid4.return_value = "42"
        prof = profiler._Profiler("secret", base_id="1", parent_id="2")
        prof.start("test")
        self.assertEqual(prof.get_parent_id(), "2")

    @mock.patch("osprofiler.profiler.uuid.uuid4")
    def test_profiler_get_base_id_unset_case(self, mock_uuid4):
        mock_uuid4.return_value = "42"
        prof = profiler._Profiler("secret")
        self.assertEqual(prof.get_base_id(), "42")
        self.assertEqual(prof.get_parent_id(), "42")

    @mock.patch("osprofiler.profiler.uuid.uuid4")
    def test_profiler_get_id(self, mock_uuid4):
        mock_uuid4.return_value = "43"
        prof = profiler._Profiler("secret")
        prof.start("test")
        self.assertEqual(prof.get_id(), "43")

    @mock.patch("osprofiler.profiler.uuid.uuid4")
    @mock.patch("osprofiler.profiler.notifier.notify")
    def test_profiler_start(self, mock_notify, mock_uuid4):
        mock_uuid4.return_value = "44"

        info = {"some": "info"}
        payload = {
            "name": "test-start",
            "base_id": "1",
            "parent_id": "2",
            "trace_id": "44",
            "info": info
        }

        prof = profiler._Profiler("secret", base_id="1", parent_id="2")
        prof.start("test", info=info)

        mock_notify.assert_called_once_with(payload)

    @mock.patch("osprofiler.profiler.notifier.notify")
    def test_profiler_stop(self, mock_notify):
        prof = profiler._Profiler("secret", base_id="1", parent_id="2")
        prof._trace_stack.append("44")
        prof._name.append("abc")

        info = {"some": "info"}
        prof.stop(info=info)

        payload = {
            "name": "abc-stop",
            "base_id": "1",
            "parent_id": "2",
            "trace_id": "44",
            "info": info
        }

        mock_notify.assert_called_once_with(payload)
        self.assertEqual(len(prof._name), 0)
        self.assertEqual(prof._trace_stack, collections.deque(["1", "2"]))

    def test_profiler_hmac(self):
        hmac = "secret"
        prof = profiler._Profiler(hmac, base_id="1", parent_id="2")
        self.assertEqual(hmac, prof.hmac_key)


class TraceTestCase(test.TestCase):

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_with_trace(self, mock_start, mock_stop):

        with profiler.Trace("a", info="a1"):
            mock_start.assert_called_once_with("a", info="a1")
            mock_start.reset_mock()
            with profiler.Trace("b", info="b1"):
                mock_start.assert_called_once_with("b", info="b1")
            mock_stop.assert_called_once_with()
            mock_stop.reset_mock()
        mock_stop.assert_called_once_with()

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_decorator_trace(self, mock_start, mock_stop):

        @profiler.trace("a", info={"b": 20})
        def method(a, b=10):
            return a + b

        self.assertEqual(40, method(10, b=30))
        expected_info = {
            "b": 20,
            "method": "tests.test_profiler.method",
            "args": str((10,)),
            "kwargs": str({"b": 30})
        }
        mock_start.assert_called_once_with("a", info=expected_info)
        mock_stop.assert_called_once_with()

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_decorator_trace_without_args(self, mock_start, mock_stop):

        @profiler.trace("a", info={}, hide_args=True)
        def method2(a, b=10):
            return a + b

        self.assertEqual(30, method2(10, b=20))
        expected_info = {"method": "tests.test_profiler.method2"}
        mock_start.assert_called_once_with("a", info=expected_info)
        mock_stop.assert_called_once_with()
