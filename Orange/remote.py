import inspect
import pkgutil
import importlib
import warnings
import pickle
from amqplib import client_0_8 as amqp
import json
import functools

import Orange

class Proxy:
    __id__ = None

    @staticmethod
    def channel() -> amqp.Channel:
        if not hasattr(Proxy, "_channel"):
            Proxy._connection = amqp.Connection()
            Proxy._channel = Proxy._connection.channel()
            Proxy._channel.queue_declare(queue="orange")
        return Proxy._channel


    def __init__(self, *args, **kwargs):
        message = json.dumps({"class": self.__class__.__module__ + "." + self.__class__.__name__,
                              "method":"__init__",
                              "args": args,
                              "kwargs": kwargs})
        Proxy.channel().basic_publish(amqp.Message(message), exchange="", routing_key="orange")

    foo = 7
    def __getattr__(self, item):
        return "5"

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
                #functions = {}
                #for name, f in inspect.getmembers(class_, inspect.isfunction):
                #    functions["name"] = Proxy.wrapped_function(f, name)

                new_class = type('%sProxy'%name, (Proxy, class_), {"__module__": modname})
                old_to_new[class_] = new_class

            setattr(module, name, new_class)
            new_to_old[new_class] = class_
    except ImportError as err:
        warnings.warn("Failed to load module %s: %s"% (modname, err))

t = Orange.data.ContinuousVariable(name="age")

Proxy._channel.close()
Proxy._connection.close()
