from http.client import HTTPConnection
import os
from socketserver import TCPServer
import threading
import unittest
from Orange.remote import create_proxy, Proxy

import Orange.server.__main__ as orange_server


class OrangeServerTests(unittest.TestCase):
    server = server_thread = None

    @classmethod
    def setUpClass(cls):
        cls.server = TCPServer(('localhost', 0), orange_server.OrangeServer)
        cls.server_thread = threading.Thread(
            name='Orange server serving',
            target=cls.server.serve_forever,
            kwargs={'poll_interval': 0.01}
        )
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server_thread.join()
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
        name, proxy = create_proxy("DummyIterable", DummyIterable)

        proxy_instance = proxy(["a"])

        self.assertEqual(len(proxy_instance), 1)
        self.assertEqual(proxy_instance[0].get(), "a")
        print(proxy_instance)
        for x in proxy_instance:
            self.assertEqual("a", x.get())


class DummyClass:
    def a(self):
        return "a"

    b = "b"

    def __str__(self):
        return "test"


class DummyIterable:
    members = ["a"]

    def __init__(self, members):
        self.members = members

    def __len__(self):
        return len(self.members)

    def __getitem__(self, item):
        return self.members[item]

    def __iter__(self):
        for x in self.members:
            yield x

    def __str__(self):
        return str(self.members)


if __name__ == '__main__':
    unittest.main()
