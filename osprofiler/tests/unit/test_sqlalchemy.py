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

import contextlib

import mock

from osprofiler import sqlalchemy
from osprofiler.tests import test


class SqlalchemyTracingTestCase(test.TestCase):

    @mock.patch("osprofiler.sqlalchemy.profiler")
    def test_before_execute(self, mock_profiler):
        handler = sqlalchemy._before_cursor_execute("sql")

        handler(mock.MagicMock(), 1, 2, 3, 4, 5)
        expected_info = {"db": {"statement": 2, "params": 3}}
        mock_profiler.start.assert_called_once_with("sql", info=expected_info)

    @mock.patch("osprofiler.sqlalchemy.profiler")
    def test_after_execute(self, mock_profiler):
        handler = sqlalchemy._after_cursor_execute()
        handler(mock.MagicMock(), 1, 2, 3, 4, 5)
        mock_profiler.stop.assert_called_once_with()

    @mock.patch("osprofiler.sqlalchemy.profiler")
    def test_after_execute_with_sql_result(self, mock_profiler):
        handler = sqlalchemy._after_cursor_execute(hide_result=False)
        cursor = mock.MagicMock()
        cursor._rows = (1,)
        handler(1, cursor, 2, 3, 4, 5)
        info = {
            "db": {
                "result": str(cursor._rows)
            }
        }
        mock_profiler.stop.assert_called_once_with(info=info)

    @mock.patch("osprofiler.sqlalchemy.profiler")
    def test_handle_error(self, mock_profiler):
        original_exception = Exception("error")
        chained_exception = Exception("error and the reason")

        sqlalchemy_exception_ctx = mock.MagicMock()
        sqlalchemy_exception_ctx.original_exception = original_exception
        sqlalchemy_exception_ctx.chained_exception = chained_exception

        sqlalchemy.handle_error(sqlalchemy_exception_ctx)
        expected_info = {
            "etype": "Exception",
            "message": "error",
            "db": {
                "original_exception": str(original_exception),
                "chained_exception": str(chained_exception),
            }
        }
        mock_profiler.stop.assert_called_once_with(info=expected_info)

    @mock.patch("osprofiler.sqlalchemy.handle_error")
    @mock.patch("osprofiler.sqlalchemy._before_cursor_execute")
    @mock.patch("osprofiler.sqlalchemy._after_cursor_execute")
    def test_add_tracing(self, mock_after_exc, mock_before_exc,
                         mock_handle_error):
        sa = mock.MagicMock()
        engine = mock.MagicMock()

        mock_before_exc.return_value = "before"
        mock_after_exc.return_value = "after"

        sqlalchemy.add_tracing(sa, engine, "sql")

        mock_before_exc.assert_called_once_with("sql")
        # Default set hide_result=True
        mock_after_exc.assert_called_once_with(hide_result=True)
        expected_calls = [
            mock.call(engine, "before_cursor_execute", "before"),
            mock.call(engine, "after_cursor_execute", "after"),
            mock.call(engine, "handle_error", mock_handle_error),
        ]
        self.assertEqual(sa.event.listen.call_args_list, expected_calls)

    @mock.patch("osprofiler.sqlalchemy.handle_error")
    @mock.patch("osprofiler.sqlalchemy._before_cursor_execute")
    @mock.patch("osprofiler.sqlalchemy._after_cursor_execute")
    def test_wrap_session(self, mock_after_exc, mock_before_exc,
                          mock_handle_error):
        sa = mock.MagicMock()

        @contextlib.contextmanager
        def _session():
            session = mock.MagicMock()
            # current engine object stored within the session
            session.bind = mock.MagicMock()
            session.bind.traced = None
            yield session

        mock_before_exc.return_value = "before"
        mock_after_exc.return_value = "after"

        session = sqlalchemy.wrap_session(sa, _session())

        with session as sess:
            pass

        mock_before_exc.assert_called_once_with("db")
        # Default set hide_result=True
        mock_after_exc.assert_called_once_with(hide_result=True)
        expected_calls = [
            mock.call(sess.bind, "before_cursor_execute", "before"),
            mock.call(sess.bind, "after_cursor_execute", "after"),
            mock.call(sess.bind, "handle_error", mock_handle_error),
        ]

        self.assertEqual(sa.event.listen.call_args_list, expected_calls)

    @mock.patch("osprofiler.sqlalchemy.handle_error")
    @mock.patch("osprofiler.sqlalchemy._before_cursor_execute")
    @mock.patch("osprofiler.sqlalchemy._after_cursor_execute")
    @mock.patch("osprofiler.profiler")
    def test_with_sql_result(self, mock_profiler, mock_after_exc,
                             mock_before_exc, mock_handle_error):
        sa = mock.MagicMock()
        engine = mock.MagicMock()

        mock_before_exc.return_value = "before"
        mock_after_exc.return_value = "after"

        sqlalchemy.add_tracing(sa, engine, "sql", hide_result=False)

        mock_before_exc.assert_called_once_with("sql")
        # Default set hide_result=True
        mock_after_exc.assert_called_once_with(hide_result=False)
        expected_calls = [
            mock.call(engine, "before_cursor_execute", "before"),
            mock.call(engine, "after_cursor_execute", "after"),
            mock.call(engine, "handle_error", mock_handle_error),
        ]
        self.assertEqual(sa.event.listen.call_args_list, expected_calls)

    @mock.patch("osprofiler.sqlalchemy._before_cursor_execute")
    @mock.patch("osprofiler.sqlalchemy._after_cursor_execute")
    def test_disable_and_enable(self, mock_after_exc, mock_before_exc):
        sqlalchemy.disable()

        sa = mock.MagicMock()
        engine = mock.MagicMock()
        sqlalchemy.add_tracing(sa, engine, "sql")
        self.assertFalse(mock_after_exc.called)
        self.assertFalse(mock_before_exc.called)

        sqlalchemy.enable()
        sqlalchemy.add_tracing(sa, engine, "sql")
        self.assertTrue(mock_after_exc.called)
        self.assertTrue(mock_before_exc.called)
