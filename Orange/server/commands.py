""" Commands that can be executed on the server. """
import importlib


class Command:
    result = None
    return_result = False

    def __init__(self, **params):
        for n, v in params.items():
            if not hasattr(self, n):
                raise AttributeError("'{}' object has no attribute '{}'".
                format(self.__class__.__name__, n))
            setattr(self, n, v)


class Create(Command):
    module = ""
    class_ = ""
    args   = ()
    kwargs = {}

    def execute(self):
        module = importlib.import_module(self.module)
        cls = getattr(module, self.class_)
        return cls(*self.args, **self.kwargs)

    def __str__(self):
        return "{}.{}(*{}, **{})".format(
            self.module, self.class_, self.args, self.kwargs
        )


class Call(Command):
    object = ""
    method = ""
    args   = ()
    kwargs = {}

    def execute(self):
        return getattr(self.object, self.method)(*self.args, **self.kwargs)

    def __str__(self):
        return "{}.{}(*{}, **{})".format(
            self.object, self.method, self.args, self.kwargs
        )


class Get(Command):
    object = ""
    member = ""

    def execute(self):
        if self.member == "":
            return self.object
        else:
            return getattr(self.object, self.member)