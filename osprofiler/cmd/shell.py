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


"""
Command-line interface to the OpenStack Profiler.
"""

import argparse
import inspect
import sys

from oslo_config import cfg

import osprofiler
from osprofiler.cmd import cliutils
from osprofiler.cmd import commands
from osprofiler import exc
from osprofiler import opts


class OSProfilerShell(object):

    def __init__(self, argv):
        args = self._get_base_parser().parse_args(argv)
        opts.set_defaults(cfg.CONF)

        if not (args.os_auth_token and args.ceilometer_url):
            if not args.os_username:
                raise exc.CommandError(
                    "You must provide a username via either --os-username or "
                    "via env[OS_USERNAME]")

            if not args.os_password:
                raise exc.CommandError(
                    "You must provide a password via either --os-password or "
                    "via env[OS_PASSWORD]")

            if self._no_project_and_domain_set(args):
                # steer users towards Keystone V3 API
                raise exc.CommandError(
                    "You must provide a project_id via either --os-project-id "
                    "or via env[OS_PROJECT_ID] and a domain_name via either "
                    "--os-user-domain-name or via env[OS_USER_DOMAIN_NAME] or "
                    "a domain_id via either --os-user-domain-id or via "
                    "env[OS_USER_DOMAIN_ID]")

            if not args.os_auth_url:
                raise exc.CommandError(
                    "You must provide an auth url via either --os-auth-url or "
                    "via env[OS_AUTH_URL]")

        args.func(args)

    def _get_base_parser(self):
        parser = argparse.ArgumentParser(
            prog="osprofiler",
            description=__doc__.strip(),
            add_help=True
        )

        parser.add_argument("-v", "--version",
                            action="version",
                            version=osprofiler.__version__)

        self._append_ceilometer_args(parser)
        self._append_identity_args(parser)
        self._append_subcommands(parser)

        return parser

    def _append_ceilometer_args(self, parent_parser):
        parser = parent_parser.add_argument_group("ceilometer")
        parser.add_argument(
            "--ceilometer-url", default=cliutils.env("CEILOMETER_URL"),
            help="Defaults to env[CEILOMETER_URL].")
        parser.add_argument(
            "--ceilometer-api-version",
            default=cliutils.env("CEILOMETER_API_VERSION", default="2"),
            help="Defaults to env[CEILOMETER_API_VERSION] or 2.")

    def _append_identity_args(self, parent_parser):
        # FIXME(fabgia): identity related parameters should be passed by the
        # Keystone client itself to avoid constant update in all the services
        # clients. When this fix is merged this method can be made obsolete.
        # Bug: https://bugs.launchpad.net/python-keystoneclient/+bug/1332337
        parser = parent_parser.add_argument_group("identity")
        parser.add_argument("-k", "--insecure",
                            default=False,
                            action="store_true",
                            help="Explicitly allow osprofiler to "
                            "perform \"insecure\" SSL (https) requests. "
                            "The server's certificate will "
                            "not be verified against any certificate "
                            "authorities. This option should be used with "
                            "caution.")

        # User related options
        parser.add_argument("--os-username",
                            default=cliutils.env("OS_USERNAME"),
                            help="Defaults to env[OS_USERNAME].")

        parser.add_argument("--os-user-id",
                            default=cliutils.env("OS_USER_ID"),
                            help="Defaults to env[OS_USER_ID].")

        parser.add_argument("--os-password",
                            default=cliutils.env("OS_PASSWORD"),
                            help="Defaults to env[OS_PASSWORD].")

        # Domain related options
        parser.add_argument("--os-user-domain-id",
                            default=cliutils.env("OS_USER_DOMAIN_ID"),
                            help="Defaults to env[OS_USER_DOMAIN_ID].")

        parser.add_argument("--os-user-domain-name",
                            default=cliutils.env("OS_USER_DOMAIN_NAME"),
                            help="Defaults to env[OS_USER_DOMAIN_NAME].")

        parser.add_argument("--os-project-domain-id",
                            default=cliutils.env("OS_PROJECT_DOMAIN_ID"),
                            help="Defaults to env[OS_PROJECT_DOMAIN_ID].")

        parser.add_argument("--os-project-domain-name",
                            default=cliutils.env("OS_PROJECT_DOMAIN_NAME"),
                            help="Defaults to env[OS_PROJECT_DOMAIN_NAME].")

        # Project V3 or Tenant V2 related options
        parser.add_argument("--os-project-id",
                            default=cliutils.env("OS_PROJECT_ID"),
                            help="Another way to specify tenant ID. "
                                 "This option is mutually exclusive with "
                                 " --os-tenant-id. "
                                 "Defaults to env[OS_PROJECT_ID].")

        parser.add_argument("--os-project-name",
                            default=cliutils.env("OS_PROJECT_NAME"),
                            help="Another way to specify tenant name. "
                                 "This option is mutually exclusive with "
                                 " --os-tenant-name. "
                                 "Defaults to env[OS_PROJECT_NAME].")

        parser.add_argument("--os-tenant-id",
                            default=cliutils.env("OS_TENANT_ID"),
                            help="This option is mutually exclusive with "
                                 " --os-project-id. "
                                 "Defaults to env[OS_PROJECT_ID].")

        parser.add_argument("--os-tenant-name",
                            default=cliutils.env("OS_TENANT_NAME"),
                            help="Defaults to env[OS_TENANT_NAME].")

        # Auth related options
        parser.add_argument("--os-auth-url",
                            default=cliutils.env("OS_AUTH_URL"),
                            help="Defaults to env[OS_AUTH_URL].")

        parser.add_argument("--os-auth-token",
                            default=cliutils.env("OS_AUTH_TOKEN"),
                            help="Defaults to env[OS_AUTH_TOKEN].")

        parser.add_argument("--os-cacert",
                            metavar="<ca-certificate-file>",
                            dest="os_cacert",
                            default=cliutils.env("OS_CACERT"),
                            help="Path of CA TLS certificate(s) used to verify"
                            " the remote server\"s certificate. Without this "
                            "option ceilometer looks for the default system CA"
                            " certificates.")

        parser.add_argument("--os-cert",
                            help="Path of certificate file to use in SSL "
                            "connection. This file can optionally be "
                            "prepended with the private key.")

        parser.add_argument("--os-key",
                            help="Path of client key to use in SSL "
                            "connection. This option is not necessary "
                            "if your key is prepended to your cert file.")

        # Service Catalog related options
        parser.add_argument("--os-service-type",
                            default=cliutils.env("OS_SERVICE_TYPE"),
                            help="Defaults to env[OS_SERVICE_TYPE].")

        parser.add_argument("--os-endpoint-type",
                            default=cliutils.env("OS_ENDPOINT_TYPE"),
                            help="Defaults to env[OS_ENDPOINT_TYPE].")

        parser.add_argument("--os-region-name",
                            default=cliutils.env("OS_REGION_NAME"),
                            help="Defaults to env[OS_REGION_NAME].")

    def _append_subcommands(self, parent_parser):
        subcommands = parent_parser.add_subparsers(help="<subcommands>")
        for group_cls in commands.BaseCommand.__subclasses__():
            group_parser = subcommands.add_parser(group_cls.group_name)
            subcommand_parser = group_parser.add_subparsers()

            for name, callback in inspect.getmembers(
                    group_cls(), predicate=inspect.ismethod):
                command = name.replace("_", "-")
                desc = callback.__doc__ or ""
                help_message = desc.strip().split("\n")[0]
                arguments = getattr(callback, "arguments", [])

                command_parser = subcommand_parser.add_parser(
                    command, help=help_message, description=desc)
                for (args, kwargs) in arguments:
                    command_parser.add_argument(*args, **kwargs)
                command_parser.set_defaults(func=callback)

    def _no_project_and_domain_set(self, args):
        if not (args.os_project_id or (args.os_project_name and
                (args.os_user_domain_name or args.os_user_domain_id)) or
                (args.os_tenant_id or args.os_tenant_name)):
            return True
        else:
            return False


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    try:
        OSProfilerShell(args)
    except exc.CommandError as e:
        print(e.message)
        return 1


if __name__ == "__main__":
    main()
