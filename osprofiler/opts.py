# Copyright 2015 OpenStack Foundation
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

from oslo_config import cfg

from osprofiler import web

__all__ = [
    "list_opts",
    "set_defaults",
]

_profiler_opt_group = cfg.OptGroup(
    "profiler",
    title="OpenStack cross-service profiling",
    help="""
OSprofiler library allows to trace requests going through various OpenStack
services and create the accumulated report of what time was spent on each
request processing step.""")

_enabled_opt = cfg.BoolOpt(
    "enabled",
    default=False,
    deprecated_group="profiler",
    deprecated_name="profiler_enabled",
    help="""
Enables the profiling for all services on this node. Default value is False
(fully disable the profiling feature).

Possible values:

* True: Enables the feature
* False: Disables the feature. The profiling cannot be started via this project
operations. If the profiling is triggered by another project, this project part
will be empty.
""")

_trace_sqlalchemy_opt = cfg.BoolOpt(
    "trace_sqlalchemy",
    default=False,
    help="""
Enables SQL requests profiling in services. Default value is False (SQL
requests won't be traced).

Possible values:

* True: Enables SQL requests profiling. Each SQL query will be part of the
trace and can the be analyzed by how much time was spent for that.
* False: Disables SQL requests profiling. The spent time is only shown on a
higher level of operations. Single SQL queries cannot be analyzed this
way.
""")

_hmac_keys_opt = cfg.StrOpt(
    "hmac_keys",
    default="SECRET_KEY",
    help="""
Secret key(s) to use for encrypting context data for performance profiling.
This string value should have the following format: <key1>[,<key2>,...<keyn>],
where each key is some random string. A user who triggers the profiling via
the REST API has to set one of these keys in the headers of the REST API call
to include profiling results of this node for this particular project.

Both "enabled" flag and "hmac_keys" config options should be set to enable
profiling. Also, to generate correct profiling information across all services
at least one key needs to be consistent between OpenStack projects. This
ensures it can be used from client side to generate the trace, containing
information from all possible resources.""")

_PROFILER_OPTS = [
    _enabled_opt,
    _trace_sqlalchemy_opt,
    _hmac_keys_opt,
]


def set_defaults(conf, enabled=None, trace_sqlalchemy=None, hmac_keys=None):
    conf.register_opts(_PROFILER_OPTS, group=_profiler_opt_group)

    if enabled is not None:
        conf.set_default("enabled", enabled,
                         group=_profiler_opt_group.name)
    if trace_sqlalchemy is not None:
        conf.set_default("trace_sqlalchemy", trace_sqlalchemy,
                         group=_profiler_opt_group.name)
    if hmac_keys is not None:
        conf.set_default("hmac_keys", hmac_keys,
                         group=_profiler_opt_group.name)


def is_trace_enabled(conf=None):
    if conf is None:
        conf = cfg.CONF
    return conf.profiler.enabled


def is_db_trace_enabled(conf=None):
    if conf is None:
        conf = cfg.CONF
    return conf.profiler.enabled and conf.profiler.trace_sqlalchemy


def enable_web_trace(conf=None):
    if conf is None:
        conf = cfg.CONF
    if conf.profiler.enabled:
        web.enable(conf.profiler.hmac_keys)


def disable_web_trace(conf=None):
    if conf is None:
        conf = cfg.CONF
    if conf.profiler.enabled:
        web.disable()


def list_opts():
    return [(_profiler_opt_group.name, _PROFILER_OPTS)]
