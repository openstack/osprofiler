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
  of the form redis://<hostname>:<port>. To use the Sentinel version
  use a connection-string of the form redissentinel://<hostname>:<port>

* Configuration

  * No config changes are required by for the base Redis driver.
  * There are two configuration options for the Redis Sentinel driver:

    * socket_timeout: specifies the sentinel connection socket timeout
      value. Defaults to: 0.1 seconds
    * sentinel_service_name: The name of the Sentinel service to use.
      Defaults to: "mymaster"
