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

============================
 Better DevStack Integration
============================

Make it simple to enable OSprofiler like it is simple to enable DEBUG log level

Problem description
===================

It's hard to turn on OSProfiler in DevStack, you have to change
notification_topic and enable Ceilometer and in future do other magic.
As well if something is done wrong it's hard to debug


Proposed change
===============

Make a single argument: PROFILING=True/False

Alternatives
------------

Do nothing and keep things hard.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  boris-42


Work Items
----------

- Make DevStack plugin for OSprofiler

- Configure Ceilometer

- Configure services that support OSprofiler


Dependencies
============

- DevStack
