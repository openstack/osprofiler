==========
Collectors
==========

There are a number of drivers to support different collector backends:

Redis
-----

* Overview

  The Redis driver allows profiling data to be collected into a redis
  database instance. The traces are stored as key-value pairs where the
  key is a string built using trace ids and timestamps and the values
  are JSON strings containing the trace information. A second driver is
  included to use Redis Sentinel in addition to single node Redis.

* Capabilities

  * Write trace data to the database.
  * Query Traces in database: This allows for pulling trace data
    querying on the keys used to save the data in the database.
  * Generate a report based on the traces stored in the database.
  * Supports use of Redis Sentinel for robustness.

* Usage

  The driver is used by OSProfiler when using a connection-string URL
  of the form redis://[:password]@host[:port][/db]. To use the Sentinel version
  use a connection-string of the form
  redissentinel://[:password]@host[:port][/db]

* Configuration

  * No config changes are required by for the base Redis driver.
  * There are two configuration options for the Redis Sentinel driver:

    * socket_timeout: specifies the sentinel connection socket timeout
      value. Defaults to: 0.1 seconds
    * sentinel_service_name: The name of the Sentinel service to use.
      Defaults to: "mymaster"

SQLAlchemy
----------

The SQLAlchemy collector allows you to store profiling data into a database
supported by SQLAlchemy.

Usage
=====
To use the driver, the `connection_string` in the `[osprofiler]` config section
needs to be set to a connection string that `SQLAlchemy understands`_
For example::

  [osprofiler]
  connection_string = mysql+pymysql://username:password@192.168.192.81/profiler?charset=utf8

where `username` is the database username, `password` is the database password,
`192.168.192.81` is the database IP address and `profiler` is the database name.

The database (in this example called `profiler`) needs to be created manually and
the database user (in this example called `username`) needs to have priviliges
to create tables and select and insert rows.

.. note::

   SQLAlchemy collector requires database JSON data type support.
   This type of data is supported by versions listed below or higher:

   - MariaDB 10.2
   - MySQL 5.7.8

.. _SQLAlchemy understands: https://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls
