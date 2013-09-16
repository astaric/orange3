import inspect
import pkgutil
import importlib
import warnings
import sys
import imp

import Orange
from Orange.remote.proxy import Proxy, get_server_address, wrapped_function, wrapped_member, create_proxy


proxies = imp.new_module('proxies')
sys.modules['proxies'] = proxies

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
                new_name, new_class = create_proxy(name, class_)
                old_to_new[class_] = new_class
                setattr(proxies, new_name, new_class)

            setattr(module, name, new_class)

    except ImportError as err:
        warnings.warn("Failed to load module %s: %s" % (modname, err))


print("Using Orange Server %s:%s" % get_server_address())
