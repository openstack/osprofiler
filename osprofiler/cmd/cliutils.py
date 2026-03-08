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

from collections.abc import Callable
import os
from typing import Any


def env(*args: str, **kwargs: str) -> str:
    """Returns the first environment variable set.

    If all are empty, defaults to '' or keyword arg `default`.
    """
    for arg in args:
        value = os.environ.get(arg)
        if value:
            return value
    return kwargs.get("default", "")


def arg(
    *args: Any, **kwargs: Any
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for CLI args.

    Example:

    >>> @arg("name", help="Name of the new entity")
        ... def entity_create(args):
        ... pass
    """

    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        add_arg(func, *args, **kwargs)
        return func

    return _decorator


def add_arg(func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Bind CLI arguments to a shell.py `do_foo` function."""

    if not hasattr(func, "arguments"):
        setattr(func, "arguments", [])

    # NOTE(sirp): avoid dups that can occur when the module is shared across
    # tests.
    if (args, kwargs) not in getattr(func, "arguments"):
        # Because of the semantics of decorator composition if we just append
        # to the options list positional options will appear to be backwards.
        getattr(func, "arguments").insert(0, (args, kwargs))
