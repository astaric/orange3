from http.client import HTTPConnection
import logging
import os
from socketserver import TCPServer
import threading
import unittest
from Orange.remote import create_proxy, Proxy
from Orange.remote.tests.dummies import DummyIterable, DummyClass

import Orange.server.__main__ as orange_server
from Orange.server.commands import ExecutionFailedError


class OrangeServerTests(unittest.TestCase):
    server = server_thread = worker = worker_thread = None

    @classmethod
    def setUpClass(cls):
        cls.server = TCPServer(('localhost', 0), orange_server.OrangeServer)
        cls.server_thread = threading.Thread(
            name='Orange server serving',
            target=cls.server.serve_forever,
            kwargs={'poll_interval': 0.01}
        )
        cls.server_thread.start()
        cls.worker = orange_server.CommandProcessor()
        cls.worker_thread = threading.Thread(
            name='Processing thread',
            target=cls.worker.run,
            kwargs={'poll_interval': 0.01}
        )
        cls.worker_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server_thread.join()
        cls.worker.shutdown()
        cls.worker_thread.join()
        cls.server.server_close()

    def setUp(self):
        os.environ["ORANGE_SERVER"] = ':'.join(map(str, self.server.server_address))
        name, self.proxy = create_proxy("DummyClass", DummyClass)

    def test_can_instantiate_proxy(self):
        self.proxy()

    def test_calling_methods_returns_a_proxy(self):
        proxy_instance = self.proxy()

        self.assertIsInstance(proxy_instance.a(), Proxy)

    def test_accessing_members_returns_a_proxy(self):
        proxy_instance = self.proxy()

        self.assertIsInstance(proxy_instance.b, Proxy)

    def test_can_proxy_iterable(self):
        FORMAT = '%(asctime)-15s %(clientip)s %(user)-8s %(message)s'
        logging.basicConfig(format=FORMAT)
        name, proxy = create_proxy("DummyIterable", DummyIterable)

        proxy_instance = proxy(["a"])

        self.assertEqual(len(proxy_instance), 1)
        self.assertEqual(len(proxy_instance), 1)
        self.assertEqual(len(proxy_instance), 1)
        self.assertEqual(proxy_instance[0].get(), "a")
        for x in proxy_instance:
            self.assertEqual("a", x.get())

    def test_raises_exception_when_remote_execution_fails(self):
        name, proxy = create_proxy("int", int)

        proxy_instance = proxy("a")

        self.assertRaises(ExecutionFailedError, proxy_instance.get)


if __name__ == '__main__':
    unittest.main()
