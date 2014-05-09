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

import mock

from osprofiler import profiler

from tests import test


class ProfilerGlobMethodsTestCase(test.TestCase):

    def test_get_profiler_not_inited(self):
        profiler._clean()
        self.assertIsNone(profiler.get_profiler())

    def test_get_profiler_and_init(self):
        p = profiler.init(base_id="1", parent_id="2")
        self.assertEqual(profiler.get_profiler(), p)

        self.assertEqual(p.get_base_id(), "1")
        # NOTE(boris-42): until we make first start we don't have
        self.assertEqual(p.get_id(), "2")

    def test_start_not_inited(self):
        profiler._clean()
        profiler.start("name")

    def test_start(self):
        p = profiler.init(base_id="1", parent_id="2")
        p.start = mock.MagicMock()
        profiler.start("name", info="info")
        p.start.assert_called_once_with("name", info="info")

    def test_stop_not_inited(self):
        profiler._clean()
        profiler.stop()

    def test_stop(self):
        p = profiler.init(base_id="1", parent_id="2")
        p.stop = mock.MagicMock()
        profiler.stop(info="info")
        p.stop.assert_called_once_with(info="info")


class ProfilerTestCase(test.TestCase):

    def test_profiler_get_base_id(self):
        prof = profiler.Profiler(base_id="1", parent_id="2")
        self.assertEqual(prof.get_base_id(), "1")

    @mock.patch("osprofiler.profiler.uuid.uuid4")
    def test_profiler_get_parent_id(self, mock_uuid4):
        mock_uuid4.return_value = "42"
        prof = profiler.Profiler(base_id="1", parent_id="2")
        prof.start("test")
        self.assertEqual(prof.get_parent_id(), "2")

    @mock.patch("osprofiler.profiler.uuid.uuid4")
    def test_profiler_get_base_id_unset_case(self, mock_uuid4):
        mock_uuid4.return_value = "42"
        prof = profiler.Profiler()
        self.assertEqual(prof.get_base_id(), "42")
        self.assertEqual(prof.get_parent_id(), "42")

    @mock.patch("osprofiler.profiler.uuid.uuid4")
    def test_profiler_get_id(self, mock_uuid4):
        mock_uuid4.return_value = "43"
        prof = profiler.Profiler()
        prof.start("test")
        self.assertEqual(prof.get_id(), "43")

    @mock.patch("osprofiler.profiler.uuid.uuid4")
    @mock.patch("osprofiler.profiler.notifier.get_notifier")
    def test_profiler_start(self, mock_get_notfier, mock_uuid4):
        mock_uuid4.return_value = "44"
        notifier = mock.MagicMock()
        mock_get_notfier.return_value = notifier

        info = {"some": "info"}
        payload = {
            "name": "test-start",
            "base_id": "1",
            "parent_id": "2",
            "trace_id": "44",
            "info": info
        }

        prof = profiler.Profiler(base_id="1", parent_id="2")
        prof.start("test", info=info)

        notifier.notify.assert_called_once_with(payload)

    @mock.patch("osprofiler.profiler.notifier.get_notifier")
    def test_profiler_stop(self, mock_get_notfier):
        notifier = mock.MagicMock()
        mock_get_notfier.return_value = notifier

        prof = profiler.Profiler(base_id="1", parent_id="2")
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

        notifier.notify.assert_called_once_with(payload)
        self.assertEqual(len(prof._name), 0)
        self.assertEqual(prof._trace_stack, ["1", "2"])

    def test_profiler_with_statement(self):
        prof = profiler.Profiler(base_id="1", parent_id="2")
        prof.start = mock.MagicMock()
        prof.stop = mock.MagicMock()

        with prof("name1", info="test"):
            prof.start.assert_called_once_with("name1", info="test")
            prof.start.reset_mock()
            self.assertFalse(prof.stop.called)
            with prof("name2", info="test2"):
                prof.start.assert_called_once_with("name2", info="test2")
                self.assertFalse(prof.stop.called)
            prof.stop.assert_called_once_with()
            prof.stop.reset_mock()
        prof.stop.assert_called_once_with()
