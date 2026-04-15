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
from collections.abc import Callable
import functools
import inspect
import socket
import threading
import types
from typing import Any, ParamSpec, TypeVar, cast

from oslo_utils import reflection
from oslo_utils import timeutils
from oslo_utils import uuidutils

from osprofiler import _utils as utils
from osprofiler import notifier


P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T", bound=type)

# NOTE(boris-42): Thread safe storage for profiler instances.
__local_ctx = threading.local()


def clean() -> None:
    __local_ctx.profiler = None


def _ensure_no_multiple_traced(
    traceable_attrs: list[tuple[str, Any]],
) -> None:
    for attr_name, attr in traceable_attrs:
        traced_times = getattr(attr, "__traced__", 0)
        if traced_times:
            raise ValueError(
                "Can not apply new trace on top of"
                f" previously traced attribute '{attr_name}' since"
                f" it has been traced {traced_times} times previously"
            )


def init(
    hmac_key: str,
    base_id: str | None = None,
    parent_id: str | None = None,
) -> "_Profiler":
    """Init profiler instance for current thread.

    You should call profiler.init() before using osprofiler.
    Otherwise profiler.start() and profiler.stop() methods won't do anything.

    :param hmac_key: secret key to sign trace information.
    :param base_id: Used to bind all related traces.
    :param parent_id: Used to build tree of traces.
    :returns: Profiler instance
    """
    if get() is None:
        __local_ctx.profiler = _Profiler(
            hmac_key, base_id=base_id, parent_id=parent_id
        )
    return cast("_Profiler", __local_ctx.profiler)


def get() -> "_Profiler | None":
    """Get profiler instance.

    :returns: Profiler instance or None if profiler wasn't inited.
    """
    return getattr(__local_ctx, "profiler", None)


def start(name: str, info: dict[str, Any] | None = None) -> None:
    """Send new start notification if profiler instance is presented.

    :param name: The name of action. E.g. wsgi, rpc, db, etc..
    :param info: Dictionary with extra trace information. For example in wsgi
                  it can be url, in rpc - message or in db sql - request.
    """
    profiler = get()
    if profiler:
        profiler.start(name, info=info)


def stop(info: dict[str, Any] | None = None) -> None:
    """Send new stop notification if profiler instance is presented."""
    profiler = get()
    if profiler:
        profiler.stop(info=info)


def trace(
    name: str,
    info: dict[str, Any] | None = None,
    hide_args: bool = False,
    hide_result: bool = True,
    allow_multiple_trace: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Trace decorator for functions.

    Very useful if you would like to add trace point on existing function:

    >>  @profiler.trace("my_point")
    >>  def my_func(self, some_args):
    >>      #code

    :param name: The name of action. E.g. wsgi, rpc, db, etc..
    :param info: Dictionary with extra trace information. For example in wsgi
                 it can be url, in rpc - message or in db sql - request.
    :param hide_args: Don't push to trace info args and kwargs. Quite useful
                      if you have some info in args that you wont to share,
                      e.g. passwords.
    :param hide_result: Boolean value to hide/show function result in trace.
                        True - hide function result (default).
                        False - show function result in trace.
    :param allow_multiple_trace: If the wrapped function has already been
                                 traced either allow the new trace to occur
                                 or raise a value error denoting that multiple
                                 tracing is not allowed (by default allow).
    """
    if not info:
        info = {}
    else:
        info = info.copy()
    info["function"] = {}

    def decorator(f: Callable[P, R]) -> Callable[P, R]:
        trace_times = getattr(f, "__traced__", 0)
        if not allow_multiple_trace and trace_times:
            raise ValueError(
                f"Function '{f}' has already been traced {trace_times} times"
            )

        try:
            setattr(f, "__traced__", trace_times + 1)
        except AttributeError:
            # Tries to work around the following:
            #
            # AttributeError: 'instancemethod' object has no
            # attribute '__traced__'
            try:
                setattr(getattr(f, "im_func"), "__traced__", trace_times + 1)
            except AttributeError:  # nosec
                pass

        @functools.wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # NOTE(tovin07): Workaround for this issue
            # F823 local variable 'info'
            # (defined in enclosing scope on line xxx)
            # referenced before assignment
            info_ = info
            if "name" not in info_["function"]:
                # Get this once (as it should **not** be changing in
                # subsequent calls).
                info_["function"]["name"] = reflection.get_callable_name(f)

            if not hide_args:
                info_["function"]["args"] = str(args)
                info_["function"]["kwargs"] = str(kwargs)

            stop_info: dict[str, Any] | None = None
            try:
                start(name, info=info_)
                result = f(*args, **kwargs)
            except Exception as ex:
                stop_info = {
                    "etype": reflection.get_class_name(ex),
                    "message": str(ex),
                }
                raise
            else:
                if not hide_result:
                    stop_info = {"function": {"result": repr(result)}}
                return result
            finally:
                stop(info=stop_info)

        return wrapper

    return decorator


def trace_cls(
    name: str,
    info: dict[str, Any] | None = None,
    hide_args: bool = False,
    hide_result: bool = True,
    trace_private: bool = False,
    allow_multiple_trace: bool = True,
    trace_class_methods: bool = False,
    trace_static_methods: bool = False,
) -> Callable[[T], T]:
    """Trace decorator for instances of class .

    Very useful if you would like to add trace point on existing method:

    >>  @profiler.trace_cls("rpc")
    >>  RpcManagerClass(object):
    >>
    >>      def my_method(self, some_args):
    >>          pass
    >>
    >>      def my_method2(self, some_arg1, some_arg2, kw=None, kw2=None)
    >>          pass
    >>

    :param name: The name of action. E.g. wsgi, rpc, db, etc..
    :param info: Dictionary with extra trace information. For example in wsgi
                 it can be url, in rpc - message or in db sql - request.
    :param hide_args: Don't push to trace info args and kwargs. Quite useful
                      if you have some info in args that you wont to share,
                      e.g. passwords.
    :param hide_result: Boolean value to hide/show function result in trace.
                        True - hide function result (default).
                        False - show function result in trace.
    :param trace_private: Trace methods that starts with "_". It wont trace
                          methods that starts "__" even if it is turned on.
    :param trace_static_methods: Trace staticmethods. This may be prone to
                                 issues so careful usage is recommended (this
                                 is also why this defaults to false).
    :param trace_class_methods: Trace classmethods. This may be prone to
                                issues so careful usage is recommended (this
                                is also why this defaults to false).
    :param allow_multiple_trace: If wrapped attributes have already been
                                 traced either allow the new trace to occur
                                 or raise a value error denoting that multiple
                                 tracing is not allowed (by default allow).
    """

    def trace_checker(
        attr_name: str, to_be_wrapped: Any
    ) -> tuple[bool, type | None]:
        if attr_name.startswith("__"):
            # Never trace really private methods.
            return (False, None)
        if not trace_private and attr_name.startswith("_"):
            return (False, None)
        if isinstance(to_be_wrapped, staticmethod):
            if not trace_static_methods:
                return (False, None)
            return (True, staticmethod)
        if isinstance(to_be_wrapped, classmethod):
            if not trace_class_methods:
                return (False, None)
            return (True, classmethod)
        return (True, None)

    def decorator(cls: T) -> T:
        clss = cls if inspect.isclass(cls) else cls.__class__
        mro_dicts = [c.__dict__ for c in inspect.getmro(clss)]
        traceable_attrs: list[tuple[str, Any]] = []
        traceable_wrappers: list[type | None] = []
        for attr_name, attr in inspect.getmembers(cls):
            if not (inspect.ismethod(attr) or inspect.isfunction(attr)):
                continue
            wrapped_obj = None
            for cls_dict in mro_dicts:
                if attr_name in cls_dict:
                    wrapped_obj = cls_dict[attr_name]
                    break
            should_wrap, wrapper = trace_checker(attr_name, wrapped_obj)
            if not should_wrap:
                continue
            traceable_attrs.append((attr_name, attr))
            traceable_wrappers.append(wrapper)
        if not allow_multiple_trace:
            # Check before doing any other further work (so we don't
            # halfway trace this class).
            _ensure_no_multiple_traced(traceable_attrs)
        for i, (attr_name, attr) in enumerate(traceable_attrs):
            wrapped_method = trace(
                name, info=info, hide_args=hide_args, hide_result=hide_result
            )(attr)
            wrapper = traceable_wrappers[i]
            if wrapper is not None:
                wrapped_method = wrapper(wrapped_method)
            setattr(cls, attr_name, wrapped_method)
        return cls

    return decorator


class TracedMeta(type):
    """Metaclass to comfortably trace all children of a specific class.

    Possible usage:

    >>>  class RpcManagerClass(object, metaclass=profiler.TracedMeta):
    >>>      __trace_args__ = {'name': 'rpc',
    >>>                        'info': None,
    >>>                        'hide_args': False,
    >>>                        'hide_result': True,
    >>>                        'trace_private': False}
    >>>
    >>>      def my_method(self, some_args):
    >>>          pass
    >>>
    >>>      def my_method2(self, some_arg1, some_arg2, kw=None, kw2=None)
    >>>          pass

    Adding of this metaclass requires to set __trace_args__ attribute to the
    class we want to modify. __trace_args__ is the dictionary with one
    mandatory key included - "name", that will define name of action to be
    traced - E.g. wsgi, rpc, db, etc...
    """

    def __init__(
        cls,
        cls_name: str,
        bases: tuple[type, ...],
        attrs: dict[str, Any],
    ) -> None:
        super().__init__(cls_name, bases, attrs)

        trace_args = dict(getattr(cls, "__trace_args__", {}))
        trace_private = trace_args.pop("trace_private", False)
        allow_multiple_trace = trace_args.pop("allow_multiple_trace", True)
        if "name" not in trace_args:
            raise TypeError(
                "Please specify __trace_args__ class level "
                "dictionary attribute with mandatory 'name' key - "
                "e.g. __trace_args__ = {'name': 'rpc'}"
            )

        traceable_attrs: list[tuple[str, Any]] = []
        for attr_name, attr_value in attrs.items():
            if not (
                inspect.ismethod(attr_value) or inspect.isfunction(attr_value)
            ):
                continue
            if attr_name.startswith("__"):
                continue
            if not trace_private and attr_name.startswith("_"):
                continue
            traceable_attrs.append((attr_name, attr_value))
        if not allow_multiple_trace:
            # Check before doing any other further work (so we don't
            # halfway trace this class).
            _ensure_no_multiple_traced(traceable_attrs)
        for attr_name, attr_value in traceable_attrs:
            setattr(
                cls, attr_name, trace(**trace_args)(getattr(cls, attr_name))
            )


class Trace:
    def __init__(self, name: str, info: dict[str, Any] | None = None) -> None:
        """With statement way to use profiler start()/stop().


        >> with profiler.Trace("rpc", info={"any": "values"})
        >>    some code

        instead of

        >> profiler.start()
        >> try:
        >>    your code
        >> finally:
              profiler.stop()
        """
        self._name = name
        self._info = info

    def __enter__(self) -> None:
        start(self._name, info=self._info)

    def __exit__(
        self,
        etype: type[BaseException] | None,
        value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        info = None
        if etype and value is not None:
            info = {
                "etype": reflection.get_class_name(etype),
                "message": value.args[0] if value.args else None,
            }
        stop(info=info)


class _Profiler:
    def __init__(
        self,
        hmac_key: str,
        base_id: str | None = None,
        parent_id: str | None = None,
    ) -> None:
        self.hmac_key = hmac_key
        if not base_id:
            base_id = str(uuidutils.generate_uuid())
        self._trace_stack: collections.deque[str] = collections.deque(
            [base_id, parent_id or base_id]
        )
        self._name: collections.deque[str] = collections.deque()
        self._host: str = socket.gethostname()

    def get_shorten_id(self, uuid_id: str | int) -> str:
        """Return shorten id of a uuid that will be used in OpenTracing drivers

        :param uuid_id: A string of uuid that was generated by uuidutils
        :returns: A shorter 64-bit long id
        """
        return format(utils.shorten_id(uuid_id), "x")

    def get_base_id(self) -> str:
        """Return base id of a trace.

        Base id is the same for all elements in one trace. It's main goal is
        to be able to retrieve by one request all trace elements from storage.
        """
        return self._trace_stack[0]

    def get_parent_id(self) -> str:
        """Returns parent trace element id."""
        return self._trace_stack[-2]

    def get_id(self) -> str:
        """Returns current trace element id."""
        return self._trace_stack[-1]

    def start(self, name: str, info: dict[str, Any] | None = None) -> None:
        """Start new event.

        Adds new trace_id to trace stack and sends notification
        to collector. With "info" and 3 ids:
        base_id - to be able to retrieve all trace elements by one query
        parent_id - to build tree of events (not just a list)
        trace_id - current event id.

        :param name: name of trace element (db, wsgi, rpc, etc..)
        :param info: Dictionary with any useful information related to this
                     trace element. (sql request, rpc message or url...)
        """

        info = info or {}
        info["host"] = self._host
        self._name.append(name)
        self._trace_stack.append(str(uuidutils.generate_uuid()))
        self._notify(f"{name}-start", info)

    def stop(self, info: dict[str, Any] | None = None) -> None:
        """Finish latest event.

        Same as a start, but instead of pushing trace_id to stack it pops it.

        :param info: Dict with useful info. It will be send in notification.
        """
        info = info or {}
        info["host"] = self._host
        # Guard against stop() being called without matching start()
        if not self._name:
            # Silently return if there's no active profiling context
            return
        self._notify(f"{self._name.pop()}-stop", info)
        if self._trace_stack:
            self._trace_stack.pop()

    def _notify(self, name: str, info: dict[str, Any]) -> None:
        payload: dict[str, Any] = {
            "name": name,
            "base_id": self.get_base_id(),
            "trace_id": self.get_id(),
            "parent_id": self.get_parent_id(),
            "timestamp": timeutils.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f"),
        }
        if info:
            payload["info"] = info

        notifier.notify(payload)
