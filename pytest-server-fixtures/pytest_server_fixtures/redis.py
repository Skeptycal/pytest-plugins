'''
Created on 25 Apr 2012

@author: eeaston

'''
from __future__ import absolute_import
import socket

import pytest
import redis

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
    port_seed = 65532

    def __init__(self, db=0, **kwargs):
        self.db = db
        super(RedisTestServer, self).__init__(**kwargs)
        self._api = None

    @property
    def _config_file(self):
        return self.workspace / 'redis.conf'

    @property
    def api(self):
        if not self._server.is_running():
            raise "Redis not ready"
        if not self._api:
            self._api = redis.Redis(host=self.hostname, port=self.port, db=self.db)
        return self._api

    @property
    def run_cmd(self):
        return [CONFIG.redis_executable, self._config_file]

    @property
    def image(self):
        return CONFIG.redis_image

    def pre_setup(self):
        # these don't work on redis-server 2.2.12 on ubuntu precise32.
        # Need to come up with a way of detecting redis server version
        # and setting the appropriate config variant.
        #
        # zset-max-ziplist-value 64
        # zset-max-ziplist-entries 128
        # vm-enabled no
        # hash-max-zipmap-entries 512
        # hash-max-zipmap-value 64
        # list-max-ziplist-entries 512
        # list-max-ziplist-value 64
        # set-max-intset-entries 512
        # activerehashing yes

        cfg = ("""
        daemonize no
        port %(port)d
        bind %(hostname)s
        timeout 0
        loglevel notice
        logfile %(workspace)s/redis.log
        databases 1
        maxmemory %(maxmemory)s
        maxmemory-policy noeviction
        appendonly no
        slowlog-log-slower-than -1
        slowlog-max-len 1024
        """ % {
            'port': self.port,
            'hostname': socket.gethostbyname(self.hostname),
            'workspace': self.workspace,
            'maxmemory': "2G",
        }).strip()
        # print "---------------\ncfg:\n%s\n---------------" % cfg

        f = open(self._config_file, "w")
        f.write(cfg)

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
