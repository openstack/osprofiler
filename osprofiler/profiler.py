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
import functools
import inspect
import threading
import uuid

from osprofiler import notifier


# NOTE(boris-42): Thread safe storage for profiler instances.
__local_ctx = threading.local()


def _clean():
    __local_ctx.profiler = None


def init(hmac_key, base_id=None, parent_id=None):
    """Init profiler instance for current thread.

    You should call profiler.init() before using osprofiler.
    Otherwise profiler.start() and profiler.stop() methods won't do anything.

    :param hmac_key: secret key to sign trace information.
    :param base_id: Used to bind all related traces.
    :param parent_id: Used to build tree of traces.
    :returns: Profiler instance
    """
    __local_ctx.profiler = _Profiler(hmac_key, base_id=base_id,
                                     parent_id=parent_id)
    return __local_ctx.profiler


def get():
    """Get profiler instance.

    :returns: Profiler instance or None if profiler wasn't inited.
    """
    return getattr(__local_ctx, "profiler", None)


def start(name, info=None):
    """Send new start notification if profiler instance is presented.

    :param name: The name of action. E.g. wsgi, rpc, db, etc..
    :param info: Dictionary with extra trace information. For example in wsgi
                  it can be url, in rpc - message or in db sql - request.
    """
    profiler = get()
    if profiler:
        profiler.start(name, info=info)


def stop(info=None):
    """Send new stop notification if profiler instance is presented."""
    profiler = get()
    if profiler:
        profiler.stop(info=info)


def trace(name, info=None, hide_args=False):
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
    """
    info = info or {}

    def decorator(f):

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            info["function"] = {"name": _get_full_func_name(f)}

            if not hide_args:
                info["function"]["args"] = str(args)
                info["function"]["kwargs"] = str(kwargs)

            with Trace(name, info=info):
                return f(*args, **kwargs)

        return wrapper

    return decorator


def trace_cls(name, info=None, hide_args=False, trace_private=False):
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

    :param trace_private: Trace methods that starts with "_". It wont trace
                          methods that starts "__" even if it is turned on.
    """

    def decorator(cls):
        for attr_name, attr in inspect.getmembers(cls):
            if not (inspect.ismethod(attr) or inspect.isfunction(attr)):
                continue
            if attr_name.startswith("__"):
                continue
            if not trace_private and attr_name.startswith("_"):
                continue

            setattr(cls, attr_name,
                    trace(name, info=info, hide_args=hide_args)(attr))
        return cls

    return decorator


class Trace(object):

    def __init__(self, name, info=None):
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

    def __enter__(self):
        start(self._name, info=self._info)

    def __exit__(self, etype, value, traceback):
        stop()


def _get_full_func_name(f):
    if hasattr(f, "__qualname__"):
        # NOTE(boris-42): Most proper way to get full name in py33
        return ".".join([f.__module__, f.__qualname__])

    if inspect.ismethod(f):
        return ".".join([f.__module__, f.im_class.__name__, f.__name__])

    return ".".join([f.__module__, f.__name__])


class _Profiler(object):

    def __init__(self, hmac_key, base_id=None, parent_id=None):
        self.hmac_key = hmac_key
        if not base_id:
            base_id = str(uuid.uuid4())
        self._trace_stack = collections.deque([base_id, parent_id or base_id])
        self._name = collections.deque()

    def get_base_id(self):
        """Return base if of trace.

        Base id is the same for all elements in one trace. It's main goal is
        to be able to retrieve by one request all trace elements from storage.
        """
        return self._trace_stack[0]

    def get_parent_id(self):
        """Returns parent trace element id."""
        return self._trace_stack[-2]

    def get_id(self):
        """Returns current trace element id."""
        return self._trace_stack[-1]

    def start(self, name, info=None):
        """Start new event.

        Adds new trace_id to trace stack and sends notification
        to collector (may be ceilometer). With "info" and 3 ids:
        base_id - to be able to retrieve all trace elements by one query
        parent_id - to build tree of events (not just a list)
        trace_id - current event id.

        As we are writing this code special for OpenStack, and there will be
        only one implementation of notifier based on ceilometer notifer api.
        That already contains timestamps, so we don't measure time by hand.

        :param name: name of trace element (db, wsgi, rpc, etc..)
        :param info: Dictionary with any useful information related to this
                     trace element. (sql request, rpc message or url...)
        """

        self._name.append(name)
        self._trace_stack.append(str(uuid.uuid4()))
        self._notify('%s-start' % name, info)

    def stop(self, info=None):
        """Finish latests event.

        Same as a start, but instead of pushing trace_id to stack it pops it.

        :param info: Dict with useful info. It will be send in notification.
        """
        self._notify('%s-stop' % self._name.pop(), info)
        self._trace_stack.pop()

    def _notify(self, name, info):
        payload = {
            'name': name,
            'base_id': self.get_base_id(),
            'trace_id': self.get_id(),
            'parent_id': self.get_parent_id()
        }
        if info:
            payload['info'] = info

        notifier.notify(payload)
