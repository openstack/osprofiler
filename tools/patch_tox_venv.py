# Copyright 2013 Red Hat, Inc.
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

import os
import sys

import install_venv_common as install_venv  # noqa


def first_file(file_list):
    for candidate in file_list:
        if os.path.exists(candidate):
            return candidate


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    venv = os.environ['VIRTUAL_ENV']

    pip_requires = first_file([
        os.path.join(root, 'requirements.txt'),
        os.path.join(root, 'tools', 'pip-requires'),
    ])
    test_requires = first_file([
        os.path.join(root, 'test-requirements.txt'),
        os.path.join(root, 'tools', 'test-requires'),
    ])
    py_version = "python{}.{}".format(sys.version_info[0], sys.version_info[1])
    project = 'oslo'
    install = install_venv.InstallVenv(root, venv, pip_requires, test_requires,
                                       py_version, project)
    # NOTE(dprince): For Tox we only run post_process, which patches files, etc
    install.post_process()


if __name__ == '__main__':
    main(sys.argv)
