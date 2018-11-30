'''
Created on 25 Apr 2012

@author: eeaston

'''
from __future__ import absolute_import
import socket

import pytest

from pytest_server_fixtures import CONFIG

from .base2 import TestServerV2


def _redis_server(request):
    """ Does the redis server work, this is used within different scoped
        fixtures.
    """
    test_server = RedisTestServer()
    request.addfinalizer(lambda p=test_server: p.teardown())
    test_server.start()
    return test_server


@pytest.fixture(scope='function')
def redis_server(request):
    """ Function-scoped Redis server in a local thread.

        Attributes
        ----------
        api: (``redis.Redis``)   Redis client API connected to this server
        .. also inherits all attributes from the `workspace` fixture
    """
    return _redis_server(request)


@pytest.fixture(scope='session')
def redis_server_sess(request):
    """ Same as redis_server fixture, scoped for test session
    """
    return _redis_server(request)


class RedisTestServer(TestServerV2):
    """This will look for 'redis_executable' in configuration and use as the
    redis-server to run.
    """

    def __init__(self, db=0, **kwargs):
        global redis
        import redis
        self.db = db
        super(RedisTestServer, self).__init__(**kwargs)
        self._api = None

    @property
    def api(self):
        if not (self._server and self._server.is_running()):
            raise "Redis not ready"
        if not self._api:
            self._api = redis.Redis(host=self.hostname, port=self.port, db=self.db)
        return self._api

    def get_cmd(self, **kwargs):
        cmd = [
            CONFIG.redis_executable,
            "--timeout", "0",
            "--loglevel", "notice",
            "--databases", "1",
            "--maxmemory", "2gb",
            "--maxmemory-policy", "noeviction",
            "--appendonly", "no",
            "--slowlog-log-slower-than", "-1",
            "--slowlog-max-len", "1024",
        ]

        if 'hostname' in kwargs:
            cmd += ["--bind", "%s" % kwargs['hostname']]
        if 'port' in kwargs:
            cmd += ["--port", "%s" % kwargs['port']]

        return cmd

    @property
    def image(self):
        return CONFIG.redis_image

    @property
    def default_port(self):
        return 6379

    def check_server_up(self):
        """ Ping the server
        """
        try:
            print("pinging Redis at %s:%s db %s" % (
                self.hostname, self.port, self.db
            ))
            return self.api.ping()
        except redis.ConnectionError as e:
            print("server not up yet (%s)" % e)
            return False
