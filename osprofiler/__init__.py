# Copyright 2011 OpenStack Foundation.
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

import importlib.metadata
import warnings


def __getattr__(name: str) -> str:
    if name == '__version__':
        warnings.warn(
            "Accessing osprofiler.__version__ is deprecated and will be "
            "removed in a future release. Use importlib.metadata instead: "
            "importlib.metadata.version('osprofiler')",
            DeprecationWarning,
            stacklevel=2,
        )
        return importlib.metadata.version('osprofiler')
    raise AttributeError(f"module 'osprofiler' has no attribute {name!r}")
