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

from osprofiler import profiler


_DISABLED = False


def disable():
    """Disable tracing of all DB queries. Reduce a lot size of profiles."""
    global _DISABLED
    _DISABLED = True


def enable():
    """add_tracing adds event listeners for sqlalchemy."""

    global _DISABLED
    _DISABLED = False


def add_tracing(sqlalchemy, engine, name, hide_result=True):
    """Add tracing to all sqlalchemy calls."""

    if not _DISABLED:
        sqlalchemy.event.listen(engine, "before_cursor_execute",
                                _before_cursor_execute(name))
        sqlalchemy.event.listen(
            engine, "after_cursor_execute",
            _after_cursor_execute(hide_result=hide_result)
        )


@contextlib.contextmanager
def wrap_session(sqlalchemy, sess):
    with sess as s:
        if not getattr(s.bind, "traced", False):
            add_tracing(sqlalchemy, s.bind, "db")
            s.bind.traced = True
        yield s


def _before_cursor_execute(name):
    """Add listener that will send trace info before query is executed."""

    def handler(conn, cursor, statement, params, context, executemany):
        info = {"db": {
            "statement": statement,
            "params": params}
        }
        profiler.start(name, info=info)

    return handler


def _after_cursor_execute(hide_result=True):
    """Add listener that will send trace info after query is executed.

    :param hide_result: Boolean value to hide or show SQL result in trace.
                        True - hide SQL result (default).
                        False - show SQL result in trace.
    """

    def handler(conn, cursor, statement, params, context, executemany):
        if not hide_result:
            # Add SQL result to trace info in *-stop phase
            info = {
                "db": {
                    "result": str(cursor._rows)
                }
            }
            profiler.stop(info=info)
        else:
            profiler.stop()

    return handler
