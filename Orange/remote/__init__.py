import inspect
import pkgutil
import importlib
import warnings
import sys
import imp

import Orange
from Orange.remote.proxy import Proxy, get_server_address, wrapped_function, wrapped_member


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
                old_to_new[class_] = new_class
                setattr(proxies, new_name, new_class)

            setattr(module, name, new_class)
            new_to_old[new_class] = class_
    except ImportError as err:
        warnings.warn("Failed to load module %s: %s" % (modname, err))


print("Using Orange Server %s:%s" % get_server_address())
