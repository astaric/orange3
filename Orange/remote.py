from http.client import HTTPConnection
import inspect
import pkgutil
import importlib
import warnings
import os
import pickle
import json
from functools import wraps
import numpy as np
import base64

import Orange


def get_server_address():
    hostname = os.environ.get('ORANGE_SERVER', "127.0.0.1")
    if ":" in hostname:
        hostname, port = hostname.split(":")
    else:
        port = 9465
    return hostname, port
print("Using Orange Server %s:%s" % get_server_address())


class ProxyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Proxy):
            return {"__jsonclass__": ('Promise', o.__id__)}
        if isinstance(o, np.ndarray):
            return {"__jsonclass__": ('PyObject', base64.b64encode(pickle.dumps(o)).decode("ascii"))}
        return json.JSONEncoder.default(self, o)


class Proxy:
    __id__ = None

    results = {}

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        if "__id__" in kwargs:
            self.__id__ = kwargs["__id__"]
        else:
            self.__id__ = cls.execute_on_server(
                "create",
                module=cls.__originalmodule__, class_=cls.__originalclass__,
                args=args, kwargs=kwargs)
        return self

    @staticmethod
    def wrapped_function(function_name, function):
        @wraps(function)
        def function(self, *args, **kwargs):
            if function_name == "__init__":
                return
            __id__ = Proxy.execute_on_server("call", object=self, method=str(function_name), args=args, kwargs=kwargs)
            return AnonymousProxy(__id__=__id__)
        return function

    @staticmethod
    def wrapped_member(member_name, member):
        @wraps(member)
        def function(self):
            __id__ = Proxy.execute_on_server("call", object=self, member=str(member_name))
            return AnonymousProxy(__id__=__id__)
        return property(function)

    def __str__(self):
        object_id = Proxy.execute_on_server("call", object=self, method="__str__")
        return Proxy.fetch_from_server(object_id)

    def get(self):
        return Proxy.fetch_from_server(self.__id__)

    def __getattr__(self, item):
        if item in {"__getnewargs__", "__getstate__", "__setstate__"}:
            raise AttributeError
        return Proxy.wrapped_member(item, lambda: None).fget(self)

    @staticmethod
    def execute_on_server(server_method, **params):
        message = ProxyEncoder().encode({server_method: params})
        connection = HTTPConnection(*get_server_address())
        connection.request("POST", server_method, message,
                           {"Content-Type": "application/json"})
        response = connection.getresponse()
        response_len = int(response.getheader("Content-Length", 0))
        response_data = response.read(response_len)
        if response.getheader("Content-Type", "") == "application/octet-stream":
            return pickle.loads(response_data)
        else:
            return response_data.decode('utf-8')

    @staticmethod
    def fetch_from_server(object_id):
        connection = HTTPConnection(*get_server_address())
        connection.request("GET", object_id)
        response = connection.getresponse()
        response_len = int(response.getheader("Content-Length", 0))
        response_data = response.read(response_len)
        if response.getheader("Content-Type", "") == "application/octet-stream":
            return pickle.loads(response_data)
        else:
            return response_data.decode('utf-8')


class AnonymousProxy(Proxy):
    def __getattribute__(self, item):
        if item in {"__id__", "get"}:
            return super().__getattribute__(item)
        return Proxy.wrapped_function(item, lambda: None)


import sys
import imp
proxies = imp.new_module('proxies')
sys.modules['proxies'] = proxies
new_to_old = {}
old_to_new = {}

excluded_modules = ["Orange.test", "Orange.remote", "Orange.server", "Orange.canvas", "Orange.widgets"]
for importer, modname, ispkg in pkgutil.walk_packages(path=Orange.__path__, prefix="Orange.", onerror=lambda x: None):
    if any(modname.startswith(excluded_module) for excluded_module in excluded_modules):
        continue
    try:
        module = importlib.import_module(modname)
        for name, class_ in inspect.getmembers(module, inspect.isclass):
            if not class_.__module__.startswith("Orange"):
                continue

            if class_ in old_to_new:
                new_class = old_to_new[class_]
            else:
                class_.__bases__ = tuple([new_to_old.get(b, b) for b in class_.__bases__])
                members = {"__module__": "proxies",
                           "__originalclass__": class_.__name__,
                           "__originalmodule__": class_.__module__}
                for n, f in inspect.getmembers(class_, inspect.isfunction):
                    if n.startswith("__"):
                        continue
                    members[n] = Proxy.wrapped_function(n, f)

                for n, p in inspect.getmembers(class_, inspect.isdatadescriptor):
                    if n.startswith("__"):
                        continue
                    members[n] = Proxy.wrapped_member(n, p)

                new_name = '%s_%s' % (class_.__module__.replace(".", "_"), name)
                new_class = type(new_name, (Proxy,), members)
                old_to_new[class_] = new_class
                setattr(proxies, new_name, new_class)

            setattr(module, name, new_class)
            new_to_old[new_class] = class_
    except ImportError as err:
        warnings.warn("Failed to load module %s: %s" % (modname, err))
