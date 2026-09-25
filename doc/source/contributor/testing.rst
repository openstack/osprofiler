=======
Testing
=======

OSProfiler provides both unit and functional tests.

Unit tests
----------

Unit tests require no external dependencies. They can be run via ``tox``.
For example:

.. code-block:: shell

   tox -e py314

Functional tests
----------------

Functional tests require a running Redis and RabbitMQ instance. You can either
install and configure these via your package manager or use a container. For
example, to start these services via ``docker``:

.. code-block:: shell

   docker run -d --name rabbitmq -p 5672:5672 rabbitmq:3
   docker run -d --name redis -p 6379:6379 redis:8

Tests can then be run via ``tox``. For example:

.. code-block:: shell

   tox -e functional-py314

Once done, you can stop and remove the containers:

.. code-block:: shell

   docker stop rabbitmq && docker rm rabbitmq
   docker stop redis && docker rm redis

Linters
-------

Linters can be run using the ``pep8`` tox target:

.. code-block:: shell

   tox -e pep8
