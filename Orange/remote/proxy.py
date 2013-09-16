import base64
from functools import wraps
from http.client import HTTPConnection
import inspect
import json
import pickle
import os

import numpy as np


def wrapped_member(member_name, member):
    @wraps(member)
    def function(self):
        __id__ = execute_on_server("call", object=self, member=str(member_name))
        return AnonymousProxy(__id__=__id__)

    return property(function)


def wrapped_function(function_name, function, synchronous=False):
    @wraps(function)
    def function(self, *args, **kwargs):
        if function_name == "__init__":
            return
        __id__ = execute_on_server("call", object=self, method=str(function_name), args=args, kwargs=kwargs)
        if synchronous:
            return fetch_from_server(__id__)
        else:
            return AnonymousProxy(__id__=__id__)

    return function


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
            self.__id__ = execute_on_server(
                "create",
                module=cls.__originalmodule__, class_=cls.__originalclass__,
                args=args, kwargs=kwargs)
        return self

    def get(self):
        return fetch_from_server(self.__id__)

    def __getattr__(self, item):
        if item in {"__getnewargs__", "__getstate__", "__setstate__"}:
            raise AttributeError
        return wrapped_member(item, lambda: None).fget(self)


class AnonymousProxy(Proxy):
    def __getattribute__(self, item):
        if item in {"__id__", "get"}:
            return super().__getattribute__(item)
        return wrapped_function(item, lambda: None)

    __str__ = wrapped_function("__str__", None, True)


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


def get_server_address():
    hostname = os.environ.get('ORANGE_SERVER', "127.0.0.1")
    if ":" in hostname:
        hostname, port = hostname.split(":")
    else:
        port = 9465
    return hostname, port


new_to_old = {}


def create_proxy(name, class_):
    class_.__bases__ = tuple([new_to_old.get(b, b) for b in class_.__bases__])
    members = {"__module__": "proxies",
               "__originalclass__": class_.__name__,
               "__originalmodule__": class_.__module__}
    for n, f in inspect.getmembers(class_, inspect.isfunction):
        synchronous = False
        if n in ("__len__", "__str__"):
            synchronous = True
        elif n.startswith("__") and n not in ("__getitem__",):
            continue
        members[n] = wrapped_function(n, f, synchronous)

    for n, p in inspect.getmembers(class_, inspect.isdatadescriptor):
        if n.startswith("__"):
            continue
        members[n] = wrapped_member(n, p)

    new_name = '%s_%s' % (class_.__module__.replace(".", "_"), name)
    new_class = type(new_name, (Proxy,), members)
    new_to_old[new_class] = class_
    return new_name, new_class
