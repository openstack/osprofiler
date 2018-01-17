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

=====================
Multi backend support
=====================

Make OSProfiler more flexible and production ready.

Problem description
===================

Currently OSprofiler works only with one backend Ceilometer which actually
doesn't work well and adds huge overhead. More over often Ceilometer is not
installed/used at all. To resolve this we should add support for different
backends like: MongoDB, InfluxDB, ElasticSearch, ...


Proposed change
===============

And new osprofiler.drivers mechanism, each driver will do 2 things:
send notifications and parse all notification in unified tree structure
that can be processed by the REST lib.

Deprecate osprofiler.notifiers and osprofiler.parsers

Change all projects that are using OSprofiler to new model

Alternatives
------------

I don't know any good alternative.

Implementation
==============

Assignee(s)
-----------

Primary assignees:
  dbelova
  ayelistratov


Work Items
----------

To add support of multi backends we should change few places in osprofiler
that are hardcoded on Ceilometer:

- CLI command ``show``:

  I believe we should add extra argument "connection_string" which will allow
  people to specify where is backend. So it will look like:
  <backend_type>://[[user[:password]]@[address][:port][/database]]

- Merge osprofiler.notifiers and osprofiler.parsers to osprofiler.drivers

  Notifiers and Parsers are tightly related. Like for MongoDB notifier you
  should use MongoDB parsers, so there is better solution to keep both
  in the same place.

  This change should be done with keeping backward compatibility,
  in other words
  we should create separated directory osprofiler.drivers and put first
  Ceilometer and then start working on other backends.

  These drivers will be chosen based on connection string

- Deprecate osprofiler.notifiers and osprofiler.parsers

- Switch all projects to new model with connection string


Dependencies
============

- Cinder, Glance, Trove, Heat should be changed
