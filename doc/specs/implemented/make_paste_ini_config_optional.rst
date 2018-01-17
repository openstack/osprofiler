..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

..
 This template should be in ReSTructured text. The filename in the git
 repository should match the launchpad URL, for example a URL of
 https://blueprints.launchpad.net/heat/+spec/awesome-thing should be named
 awesome-thing.rst .  Please do not delete any of the sections in this
 template.  If you have nothing to say for a whole section, just write: None
 For help with syntax, see http://www.sphinx-doc.org/en/stable/rest.html
 To test out your formatting, see http://www.tele3.cz/jbar/rest/rest.html

======================================
 Make api-paste.ini Arguments Optional
======================================

Problem description
===================

Integration of OSprofiler with OpenStack projects is harder than it should be,
it requires keeping part of arguments inside api-paste.ini files and part in
projects.conf file.

We should make all configuration options from api-paste.ini file optional
and add alternative way to configure osprofiler.web.WsgiMiddleware


Proposed change
===============

Integration of OSprofiler requires 2 changes in api-paste.ini file:

- One is adding osprofiler.web.WsgiMiddleware to pipelines:
  https://github.com/openstack/cinder/blob/master/etc/cinder/api-paste.ini#L13

- Another is to add it's arguments:
  https://github.com/openstack/cinder/blob/master/etc/cinder/api-paste.ini#L31-L32

  so WsgiMiddleware will be correctly initialized here:
  https://github.com/openstack/osprofiler/blob/51761f375189bdc03b7e72a266ad0950777f32b1/osprofiler/web.py#L64

We should make ``hmac_keys`` and ``enabled``  variable optional, create
separated method from initialization of wsgi middleware and cut new release.
After that remove


Alternatives
------------

None.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  dbelova

Work Items
----------

- Modify osprofiler.web.WsgiMiddleware to make ``hmac_keys`` optional (done)

- Add alternative way to setup osprofiler.web.WsgiMiddleware, e.g. extra
  argument hmac_keys to enable() method (done)

- Cut new release 0.3.1 (tbd)

- Fix the code in all projects: remove api-paste.ini arguments and use
  osprofiler.web.enable with extra argument (tbd)


Dependencies
============

- Cinder, Glance, Trove - projects should be fixed
