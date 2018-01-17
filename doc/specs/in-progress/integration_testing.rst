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

===================
Integration Testing
===================

We should create DSVM job that check that proposed changes in OSprofiler
don't break projects that are using OSProfiler.


Problem description
===================

Currently we don't have CI for testing that OSprofiler changes are backward
compatible and don't break projects that are using OSprofiler. In other words
without this job each time when we are releasing OSProfiler we can break
some of OpenStack projects which is quite bad.

Proposed change
===============

Create DSVM job that will install OSprofiler with proposed patch instead of
the latest release and run some basic tests.

Alternatives
------------

Do nothing and break the OpenStack..

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  <launchpad-id or None>


Work Items
----------

- Create DSVM job
- Run Rally tests to make sure that everything works


Dependencies
============

None
