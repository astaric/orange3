import inspect
import pkgutil
import importlib, imp
import warnings
import pickle
from amqplib import client_0_8 as amqp
import json
from functools import wraps
import uuid
import numpy as np
import base64

import Orange

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

    connection = amqp.Connection()
    channel = connection.channel()
    channel.queue_declare(queue="orange")

    callback_queue, _, _ = channel.queue_declare(exclusive=True)
    def on_response(message : amqp.Message):
        Proxy.results[message.properties["correlation_id"]] = pickle.loads(message.body)
    channel.basic_consume(callback=on_response, no_ack=True,
        queue=callback_queue)

    def __new__(cls, *args, **kwargs):
        self = object.__new__(cls)
        if "__id__" in kwargs:
            self.__id__ = kwargs["__id__"]
        else:
            self.__id__ = str(uuid.uuid1())
            message = ProxyEncoder().encode({"create": {"module": cls.__originalmodule__,
                                                        "class_":  cls.__originalclass__,
                                                        "args": args,
                                                        "kwargs": kwargs,
                                                        "result": self.__id__,}})
            Proxy.apply_async(message)
        return self

    @staticmethod
    def disconnect():
        Proxy.channel.close()
        Proxy.connection.close()

    @staticmethod
    def apply_async(message):
        requestid = str(uuid.uuid4())
        message = amqp.Message(message, correlation_id=requestid, reply_to=Proxy.callback_queue)
        Proxy.channel.basic_publish(message, exchange="", routing_key="orange")

    @staticmethod
    def apply_sync(message):
        requestid = str(uuid.uuid4())
        message = amqp.Message(message, correlation_id=requestid, reply_to=Proxy.callback_queue)
        Proxy.channel.basic_publish(message, exchange="", routing_key="orange")

        while requestid not in Proxy.results:
            Proxy.channel.wait()
        return Proxy.results[requestid]

    @staticmethod
    def wrapped_function(name, f):
        @wraps(f)
        def function(self, *args, **kwargs):
            if name == "__init__":
                return
            __id__ = str(uuid.uuid1())
            message = ProxyEncoder().encode({"call": {"object": self,
                                                      "method": str(name),
                                                      "args": args,
                                                      "kwargs":kwargs,
                                                      "result": __id__,}})
            Proxy.apply_async(message)
            return AnonymousProxy(__id__=__id__)
        return function

    @staticmethod
    def wrapped_member(name, f):
        @wraps(f)
        def function(self):
            __id__ = str(uuid.uuid1())
            message = ProxyEncoder().encode({"get": {"object": self,
                                                     "member": name,
                                                     "result": __id__}})
            Proxy.apply_async(message)
            return AnonymousProxy(__id__=__id__)
        return property(function)

    def __str__(self):
        __id__ = str(uuid.uuid1())
        message = ProxyEncoder().encode({"call": {"object": self,
                                                  "method": "__str__",
                                                  "result": __id__,
                                                  "return_result": True}})
        return Proxy.apply_sync(message)

    def get(self):
        message = ProxyEncoder().encode({"get": {"object": self}})
        return Proxy.apply_sync(message)

    def __getattr__(self, item):
        if item in {"__getnewargs__", "__getstate__", "__setstate__"}: raise AttributeError
        return Proxy.wrapped_member(item, lambda:None).fget(self)


class AnonymousProxy(Proxy):
    def __getattribute__(self, item):
        if item in {"__id__", "get"}:
            return super().__getattribute__(item)
        return Proxy.wrapped_function(item, lambda:None)


import sys, imp
proxies = imp.new_module('proxies')
sys.modules['proxies'] = proxies
new_to_old = {}
old_to_new = {}

for importer, modname, ispkg in pkgutil.walk_packages(path=Orange.__path__, prefix="Orange.", onerror=lambda x: None):
    if modname.startswith("Orange.test") or modname.startswith("Orange.remote") or modname.startswith("Orange.server"):
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
                           "__originalmodule__":class_.__module__ }
                for n, f in inspect.getmembers(class_, inspect.isfunction):
                    if n.startswith("__"): continue
                    members[n] = Proxy.wrapped_function(n, f)

                for n, p in inspect.getmembers(class_, inspect.isdatadescriptor):
                    if n.startswith("__"): continue
                    members[n] = Proxy.wrapped_member(n, p)

                newname = '%s_%s'% (class_.__module__.replace(".", "_"), name)
                new_class = type(newname, (Proxy,), members)
                old_to_new[class_] = new_class
                setattr(proxies, newname, new_class)

            setattr(module, name, new_class)
            new_to_old[new_class] = class_
    except ImportError as err:
        warnings.warn("Failed to load module %s: %s"% (modname, err))

