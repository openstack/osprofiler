# Copyright 2018 Fujitsu Ltd.
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

from typing import Any

from oslo_config import cfg

from osprofiler.drivers import base
from osprofiler import exc


# TODO(tkajinam): Remove this and the deprecated options after G-release
class Jaeger(base.Driver):
    def __init__(
        self,
        connection_str: str,
        project: str | None = None,
        service: str | None = None,
        host: str | None = None,
        conf: cfg.ConfigOpts | None = None,
        **kwargs: Any,
    ) -> None:
        """Jaeger driver for OSProfiler."""

        raise exc.CommandError('Jaeger driver is no longer supported')

    @classmethod
    def get_name(cls) -> str:
        return "jaeger"
