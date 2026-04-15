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

from collections.abc import Generator
import contextlib
import logging as log
from typing import Any

from oslo_utils import reflection

from osprofiler import profiler

LOG = log.getLogger(__name__)

_DISABLED = False


def disable() -> None:
    """Disable tracing of all DB queries. Reduce a lot size of profiles."""
    global _DISABLED
    _DISABLED = True


def enable() -> None:
    """add_tracing adds event listeners for sqlalchemy."""

    global _DISABLED
    _DISABLED = False


def add_tracing(
    sqlalchemy: Any, engine: Any, name: str, hide_result: bool = True
) -> None:
    """Add tracing to all sqlalchemy calls."""

    if not _DISABLED:
        sqlalchemy.event.listen(
            engine, "before_cursor_execute", _before_cursor_execute(name)
        )
        sqlalchemy.event.listen(
            engine,
            "after_cursor_execute",
            _after_cursor_execute(hide_result=hide_result),
        )
        sqlalchemy.event.listen(engine, "handle_error", handle_error)


@contextlib.contextmanager
def wrap_session(sqlalchemy: Any, sess: Any) -> Generator[Any, None, None]:
    with sess as s:
        if not getattr(s.bind, "traced", False):
            add_tracing(sqlalchemy, s.bind, "db")
            s.bind.traced = True
        yield s


def _before_cursor_execute(name: str) -> Any:
    """Add listener that will send trace info before query is executed."""

    def handler(
        conn: Any,
        cursor: Any,
        statement: Any,
        params: Any,
        context: Any,
        executemany: Any,
    ) -> None:
        info = {"db": {"statement": statement, "params": params}}
        profiler.start(name, info=info)

    return handler


def _after_cursor_execute(hide_result: bool = True) -> Any:
    """Add listener that will send trace info after query is executed.

    :param hide_result: Boolean value to hide or show SQL result in trace.
                        True - hide SQL result (default).
                        False - show SQL result in trace.
    """

    def handler(
        conn: Any,
        cursor: Any,
        statement: Any,
        params: Any,
        context: Any,
        executemany: Any,
    ) -> None:
        if not hide_result:
            # Add SQL result to trace info in *-stop phase
            info = {"db": {"result": str(cursor._rows)}}
            profiler.stop(info=info)
        else:
            profiler.stop()

    return handler


def handle_error(exception_context: Any) -> None:
    """Handle SQLAlchemy errors"""
    exception_class_name = reflection.get_class_name(
        exception_context.original_exception
    )
    original_exception = str(exception_context.original_exception)

    # SQLAlchemy 2.0 removed chained_exception attribute.
    # Fall back to Python's standard exception chaining (__cause__)
    if hasattr(exception_context, 'chained_exception'):
        # SQLAlchemy 1.x
        chained_exception = str(exception_context.chained_exception)
    else:
        # SQLAlchemy 2.0+ - use Python's standard exception chain
        cause = exception_context.original_exception.__cause__
        chained_exception = str(cause) if cause else ''

    info = {
        "etype": exception_class_name,
        "message": original_exception,
        "db": {
            "original_exception": original_exception,
            "chained_exception": chained_exception,
        },
    }
    profiler.stop(info=info)
    LOG.debug(
        "OSProfiler has handled SQLAlchemy error: %s", original_exception
    )
