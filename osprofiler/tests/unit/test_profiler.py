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
import copy
import datetime
import re

import mock
import six

from osprofiler import profiler
from osprofiler.tests import test


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

    @mock.patch("osprofiler.profiler.uuidutils.generate_uuid")
    def test_profiler_get_parent_id(self, mock_generate_uuid):
        mock_generate_uuid.return_value = "42"
        prof = profiler._Profiler("secret", base_id="1", parent_id="2")
        prof.start("test")
        self.assertEqual(prof.get_parent_id(), "2")

    @mock.patch("osprofiler.profiler.uuidutils.generate_uuid")
    def test_profiler_get_base_id_unset_case(self, mock_generate_uuid):
        mock_generate_uuid.return_value = "42"
        prof = profiler._Profiler("secret")
        self.assertEqual(prof.get_base_id(), "42")
        self.assertEqual(prof.get_parent_id(), "42")

    @mock.patch("osprofiler.profiler.uuidutils.generate_uuid")
    def test_profiler_get_id(self, mock_generate_uuid):
        mock_generate_uuid.return_value = "43"
        prof = profiler._Profiler("secret")
        prof.start("test")
        self.assertEqual(prof.get_id(), "43")

    @mock.patch("osprofiler.profiler.datetime")
    @mock.patch("osprofiler.profiler.uuidutils.generate_uuid")
    @mock.patch("osprofiler.profiler.notifier.notify")
    def test_profiler_start(self, mock_notify, mock_generate_uuid,
                            mock_datetime):
        mock_generate_uuid.return_value = "44"
        now = datetime.datetime.utcnow()
        mock_datetime.datetime.utcnow.return_value = now

        info = {"some": "info"}
        payload = {
            "name": "test-start",
            "base_id": "1",
            "parent_id": "2",
            "trace_id": "44",
            "info": info,
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.%f"),
        }

        prof = profiler._Profiler("secret", base_id="1", parent_id="2")
        prof.start("test", info=info)

        mock_notify.assert_called_once_with(payload)

    @mock.patch("osprofiler.profiler.datetime")
    @mock.patch("osprofiler.profiler.notifier.notify")
    def test_profiler_stop(self, mock_notify, mock_datetime):
        now = datetime.datetime.utcnow()
        mock_datetime.datetime.utcnow.return_value = now
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
            "info": info,
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.%f"),
        }

        mock_notify.assert_called_once_with(payload)
        self.assertEqual(len(prof._name), 0)
        self.assertEqual(prof._trace_stack, collections.deque(["1", "2"]))

    def test_profiler_hmac(self):
        hmac = "secret"
        prof = profiler._Profiler(hmac, base_id="1", parent_id="2")
        self.assertEqual(hmac, prof.hmac_key)


class WithTraceTestCase(test.TestCase):

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
    def test_with_trace_etype(self, mock_start, mock_stop):

        def foo():
            with profiler.Trace("foo"):
                raise ValueError("bar")

        self.assertRaises(ValueError, foo)
        mock_start.assert_called_once_with("foo", info=None)
        mock_stop.assert_called_once_with(info={"etype": "ValueError"})


@profiler.trace("function", info={"info": "some_info"})
def tracede_func(i):
    return i


@profiler.trace("hide_args", hide_args=True)
def trace_hide_args_func(a, i=10):
    return (a, i)


class TraceDecoratorTestCase(test.TestCase):

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_duplicate_trace_disallow(self, mock_start, mock_stop):

        @profiler.trace("test")
        def trace_me():
            pass

        self.assertRaises(
            ValueError,
            profiler.trace("test-again", allow_multiple_trace=False),
            trace_me)

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_with_args(self, mock_start, mock_stop):
        self.assertEqual(1, tracede_func(1))
        expected_info = {
            "info": "some_info",
            "function": {
                "name": "osprofiler.tests.unit.test_profiler.tracede_func",
                "args": str((1,)),
                "kwargs": str({})
            }
        }
        mock_start.assert_called_once_with("function", info=expected_info)
        mock_stop.assert_called_once_with()

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_without_args(self, mock_start, mock_stop):
        self.assertEqual((1, 2), trace_hide_args_func(1, i=2))
        expected_info = {
            "function": {
                "name": "osprofiler.tests.unit.test_profiler"
                        ".trace_hide_args_func"
            }
        }
        mock_start.assert_called_once_with("hide_args", info=expected_info)
        mock_stop.assert_called_once_with()


class FakeTracedCls(object):

    def method1(self, a, b, c=10):
        return a + b + c

    def method2(self, d, e):
        return d - e

    def method3(self, g=10, h=20):
        return g * h

    def _method(self, i):
        return i


@profiler.trace_cls("rpc", info={"a": 10})
class FakeTraceClassWithInfo(FakeTracedCls):
    pass


@profiler.trace_cls("a", info={"b": 20}, hide_args=True)
class FakeTraceClassHideArgs(FakeTracedCls):
    pass


@profiler.trace_cls("rpc", trace_private=True)
class FakeTracePrivate(FakeTracedCls):
    pass


class FakeTraceStaticMethodBase(FakeTracedCls):
    @staticmethod
    def static_method(arg):
        return arg


@profiler.trace_cls("rpc", trace_static_methods=True)
class FakeTraceStaticMethod(FakeTraceStaticMethodBase):
    pass


@profiler.trace_cls("rpc")
class FakeTraceStaticMethodSkip(FakeTraceStaticMethodBase):
    pass


class FakeTraceClassMethodBase(FakeTracedCls):
    @classmethod
    def class_method(cls, arg):
        return arg


@profiler.trace_cls("rpc")
class FakeTraceClassMethodSkip(FakeTraceClassMethodBase):
    pass


def py3_info(info):
    # NOTE(boris-42): py33 I hate you.
    info_py3 = copy.deepcopy(info)
    new_name = re.sub("FakeTrace[^.]*", "FakeTracedCls",
                      info_py3["function"]["name"])
    info_py3["function"]["name"] = new_name
    return info_py3


def possible_mock_calls(name, info):
    # NOTE(boris-42): py33 I hate you.
    return [mock.call(name, info=info), mock.call(name, info=py3_info(info))]


class TraceClsDecoratorTestCase(test.TestCase):

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_args(self, mock_start, mock_stop):
        fake_cls = FakeTraceClassWithInfo()
        self.assertEqual(30, fake_cls.method1(5, 15))
        expected_info = {
            "a": 10,
            "function": {
                "name": ("osprofiler.tests.unit.test_profiler"
                         ".FakeTraceClassWithInfo.method1"),
                "args": str((fake_cls, 5, 15)),
                "kwargs": str({})
            }
        }
        self.assertEqual(1, len(mock_start.call_args_list))
        self.assertIn(mock_start.call_args_list[0],
                      possible_mock_calls("rpc", expected_info))
        mock_stop.assert_called_once_with()

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_kwargs(self, mock_start, mock_stop):
        fake_cls = FakeTraceClassWithInfo()
        self.assertEqual(50, fake_cls.method3(g=5, h=10))
        expected_info = {
            "a": 10,
            "function": {
                "name": ("osprofiler.tests.unit.test_profiler"
                         ".FakeTraceClassWithInfo.method3"),
                "args": str((fake_cls,)),
                "kwargs": str({"g": 5, "h": 10})
            }
        }
        self.assertEqual(1, len(mock_start.call_args_list))
        self.assertIn(mock_start.call_args_list[0],
                      possible_mock_calls("rpc", expected_info))
        mock_stop.assert_called_once_with()

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_without_private(self, mock_start, mock_stop):
        fake_cls = FakeTraceClassHideArgs()
        self.assertEqual(10, fake_cls._method(10))
        self.assertFalse(mock_start.called)
        self.assertFalse(mock_stop.called)

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_without_args(self, mock_start, mock_stop):
        fake_cls = FakeTraceClassHideArgs()
        self.assertEqual(40, fake_cls.method1(5, 15, c=20))
        expected_info = {
            "b": 20,
            "function": {
                "name": ("osprofiler.tests.unit.test_profiler"
                         ".FakeTraceClassHideArgs.method1"),
            }
        }

        self.assertEqual(1, len(mock_start.call_args_list))
        self.assertIn(mock_start.call_args_list[0],
                      possible_mock_calls("a", expected_info))
        mock_stop.assert_called_once_with()

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_private_methods(self, mock_start, mock_stop):
        fake_cls = FakeTracePrivate()
        self.assertEqual(5, fake_cls._method(5))

        expected_info = {
            "function": {
                "name": ("osprofiler.tests.unit.test_profiler"
                         ".FakeTracePrivate._method"),
                "args": str((fake_cls, 5)),
                "kwargs": str({})
            }
        }

        self.assertEqual(1, len(mock_start.call_args_list))
        self.assertIn(mock_start.call_args_list[0],
                      possible_mock_calls("rpc", expected_info))
        mock_stop.assert_called_once_with()

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    @test.testcase.skip(
        "Static method tracing was disabled due the bug. This test should be "
        "skipped until we find the way to address it.")
    def test_static(self, mock_start, mock_stop):
        fake_cls = FakeTraceStaticMethod()

        self.assertEqual(25, fake_cls.static_method(25))

        expected_info = {
            "function": {
                # fixme(boris-42): Static methods are treated differently in
                #                  Python 2.x and Python 3.x. So in PY2 we
                #                  expect to see method4 because method is
                #                  static and doesn't have reference to class
                #                  - and FakeTraceStatic.method4 in PY3
                "name":
                    "osprofiler.tests.unit.test_profiler"
                    ".method4" if six.PY2 else
                    "osprofiler.tests.unit.test_profiler.FakeTraceStatic"
                    ".method4",
                "args": str((25,)),
                "kwargs": str({})
            }
        }

        self.assertEqual(1, len(mock_start.call_args_list))
        self.assertIn(mock_start.call_args_list[0],
                      possible_mock_calls("rpc", expected_info))
        mock_stop.assert_called_once_with()

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_static_method_skip(self, mock_start, mock_stop):
        self.assertEqual(25, FakeTraceStaticMethodSkip.static_method(25))
        self.assertFalse(mock_start.called)
        self.assertFalse(mock_stop.called)

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_class_method_skip(self, mock_start, mock_stop):
        self.assertEqual("foo", FakeTraceClassMethodSkip.class_method("foo"))
        self.assertFalse(mock_start.called)
        self.assertFalse(mock_stop.called)


@six.add_metaclass(profiler.TracedMeta)
class FakeTraceWithMetaclassBase(object):
    __trace_args__ = {"name": "rpc",
                      "info": {"a": 10}}

    def method1(self, a, b, c=10):
        return a + b + c

    def method2(self, d, e):
        return d - e

    def method3(self, g=10, h=20):
        return g * h

    def _method(self, i):
        return i


class FakeTraceDummy(FakeTraceWithMetaclassBase):
    def method4(self, j):
        return j


class FakeTraceWithMetaclassHideArgs(FakeTraceWithMetaclassBase):
    __trace_args__ = {"name": "a",
                      "info": {"b": 20},
                      "hide_args": True}

    def method5(self, k, l):
        return k + l


class FakeTraceWithMetaclassPrivate(FakeTraceWithMetaclassBase):
    __trace_args__ = {"name": "rpc",
                      "trace_private": True}

    def _new_private_method(self, m):
        return 2 * m


class TraceWithMetaclassTestCase(test.TestCase):

    def test_no_name_exception(self):
        def define_class_with_no_name():
            @six.add_metaclass(profiler.TracedMeta)
            class FakeTraceWithMetaclassNoName(FakeTracedCls):
                pass
        self.assertRaises(TypeError, define_class_with_no_name, 1)

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_args(self, mock_start, mock_stop):
        fake_cls = FakeTraceWithMetaclassBase()
        self.assertEqual(30, fake_cls.method1(5, 15))
        expected_info = {
            "a": 10,
            "function": {
                "name": ("osprofiler.tests.unit.test_profiler"
                         ".FakeTraceWithMetaclassBase.method1"),
                "args": str((fake_cls, 5, 15)),
                "kwargs": str({})
            }
        }
        self.assertEqual(1, len(mock_start.call_args_list))
        self.assertIn(mock_start.call_args_list[0],
                      possible_mock_calls("rpc", expected_info))
        mock_stop.assert_called_once_with()

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_kwargs(self, mock_start, mock_stop):
        fake_cls = FakeTraceWithMetaclassBase()
        self.assertEqual(50, fake_cls.method3(g=5, h=10))
        expected_info = {
            "a": 10,
            "function": {
                "name": ("osprofiler.tests.unit.test_profiler"
                         ".FakeTraceWithMetaclassBase.method3"),
                "args": str((fake_cls,)),
                "kwargs": str({"g": 5, "h": 10})
            }
        }
        self.assertEqual(1, len(mock_start.call_args_list))
        self.assertIn(mock_start.call_args_list[0],
                      possible_mock_calls("rpc", expected_info))
        mock_stop.assert_called_once_with()

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_without_private(self, mock_start, mock_stop):
        fake_cls = FakeTraceWithMetaclassHideArgs()
        self.assertEqual(10, fake_cls._method(10))
        self.assertFalse(mock_start.called)
        self.assertFalse(mock_stop.called)

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_without_args(self, mock_start, mock_stop):
        fake_cls = FakeTraceWithMetaclassHideArgs()
        self.assertEqual(20, fake_cls.method5(5, 15))
        expected_info = {
            "b": 20,
            "function": {
                "name": ("osprofiler.tests.unit.test_profiler"
                         ".FakeTraceWithMetaclassHideArgs.method5")
            }
        }

        self.assertEqual(1, len(mock_start.call_args_list))
        self.assertIn(mock_start.call_args_list[0],
                      possible_mock_calls("a", expected_info))
        mock_stop.assert_called_once_with()

    @mock.patch("osprofiler.profiler.stop")
    @mock.patch("osprofiler.profiler.start")
    def test_private_methods(self, mock_start, mock_stop):
        fake_cls = FakeTraceWithMetaclassPrivate()
        self.assertEqual(10, fake_cls._new_private_method(5))

        expected_info = {
            "function": {
                "name": ("osprofiler.tests.unit.test_profiler"
                         ".FakeTraceWithMetaclassPrivate._new_private_method"),
                "args": str((fake_cls, 5)),
                "kwargs": str({})
            }
        }

        self.assertEqual(1, len(mock_start.call_args_list))
        self.assertIn(mock_start.call_args_list[0],
                      possible_mock_calls("rpc", expected_info))
        mock_stop.assert_called_once_with()
