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

from osprofiler import _utils as utils


class Notifier(object):

    def notify(self, info):
        """This method will be called on each notifier.notify() call.

        To add new drivers you should, create new subclass of this class and
        implement notify method.
        """

    @staticmethod
    def factory(name, *args, **kwargs):
        for driver in utils.itersubclasses(Notifier):
            if name == driver.__name__:
                return driver(*args, **kwargs).notify

        raise TypeError("There is no driver, with name: %s" % name)
