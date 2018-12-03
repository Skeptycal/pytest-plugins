import os
import tempfile
import shutil
import subprocess
import time
import errno
import logging
import getpass

import pytest

from pytest_server_fixtures import CONFIG

from .base2 import TestServerV2

log = logging.getLogger(__name__)


def _mongo_server():
    """ This does the actual work - there are several versions of this used
        with different scopes.
    """
    test_server = MongoTestServer()
    try:
        test_server.start()
        yield test_server
    finally:
        test_server.teardown()


@pytest.yield_fixture(scope='function')
def mongo_server():
    """ Function-scoped MongoDB server started in a local thread.
        This also provides a temp workspace.
        We tear down, and cleanup mongos at the end of the test.

        For completeness, we tidy up any outstanding mongo temp directories
        at the start and end of each test session

        Attributes
        ----------
        api (`pymongo.MongoClient`)  : PyMongo Client API connected to this server
        .. also inherits all attributes from the `workspace` fixture
    """
    for server in _mongo_server():
        yield server


@pytest.yield_fixture(scope='session')
def mongo_server_sess():
    """ Same as mongo_server fixture, scoped as session instead.
    """
    for server in _mongo_server():
        yield server


@pytest.yield_fixture(scope='class')
def mongo_server_cls(request):
    """ Same as mongo_server fixture, scoped for test classes.
    """
    for server in _mongo_server():
        request.cls.mongo_server = server
        yield server


@pytest.yield_fixture(scope='module')
def mongo_server_module():
    """ Same as mongo_server fixture, scoped for test modules.
    """
    for server in _mongo_server():
        yield server


class MongoTestServer(TestServerV2):

    def __init__(self, delete=True, **kwargs):
        super(MongoTestServer, self).__init__(delete=delete, **kwargs)
        self._port = self._get_port(27017)

    def get_cmd(self, **kwargs):
        cmd = [
            CONFIG.mongo_executable,
            '--port=%s' % self.port,
            '--nounixsocket',
            '--syncdelay=0',
            '--nojournal',
            '--quiet',
        ]

        if 'hostname' in kwargs:
            cmd.append('--bind_ip=%s' % kwargs['hostname'])
        if 'workspace' in kwargs:
            cmd.append('--dbpath=%s' % str(kwargs['workspace']))

        return cmd

    @property
    def image(self):
        return CONFIG.mongo_image

    @property
    def port(self):
        return self._port

    def check_server_up(self):
        """Test connection to the server."""
        import pymongo
        from pymongo.errors import AutoReconnect, ConnectionFailure

        log.info("Connecting to Mongo at %s:%s" % (self.hostname, self.port))
        try:
            self.api = pymongo.MongoClient(self.hostname, self.port,
                                           serverselectiontimeoutms=200)
            self.api.list_database_names()
            # Configure the client with default timeouts in case the server goes slow
            self.api = pymongo.MongoClient(self.hostname, self.port)
            return True
        except (AutoReconnect, ConnectionFailure) as e:
            pass
        return False

