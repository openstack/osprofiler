# Copyright 2016 Mirantis Inc.
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

import oslo_messaging

from osprofiler import notifier
from osprofiler import web


def init_from_conf(conf, context, project, service, host):
    """Initialize notifier from service configuration

    :param conf: service configuration
    :param context: request context
    :param project: project name (keystone, cinder etc.)
    :param service: service name that will be profiled
    :param host: hostname or host IP address that the service will be
                 running on.
    """
    connection_str = conf.profiler.connection_string
    kwargs = {}
    if connection_str.startswith("messaging"):
        kwargs = {"messaging": oslo_messaging,
                  "transport": oslo_messaging.get_notification_transport(conf)}
    _notifier = notifier.create(
        connection_str,
        context=context,
        project=project,
        service=service,
        host=host,
        conf=conf,
        **kwargs)
    notifier.set(_notifier)
    web.enable(conf.profiler.hmac_keys)
