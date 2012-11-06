from amqplib import client_0_8 as amqp
import json, pickle
import importlib
import base64
import logging

cache = {}

class Command:
    result = None
    return_result = False

    def __init__(self, **params):
        for n, v in params.items():
            if not hasattr(self, n):
                logging.error(params.items())
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
        return getattr(self.object, self.member)


class Promise:
    def __init__(self, id):
        self.id = id

    def get(self, id):
        return cache[id]

    def ready(self, id):
        return id in cache


class Proxy:
    __id__ = None

    def __init__(self, id):
        self.__id__ = id

class Server:
    def __init__(self):
        self.logger = logging.getLogger("Server")

        self.connection = amqp.Connection()
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue="orange")
        self.cache = {}
        self.channel.basic_consume(queue="orange", callback=self.data_received)
        self.logger.info(" [*] Waiting for messages. To exit press CTRL+C")

    def start(self):
        try:
            while True:
                self.channel.wait()
        except KeyboardInterrupt:
            pass
        self.channel.close()
        self.connection.close()
        self.logger.info(" [*] Closing connection")


    def data_received(self, msg : amqp.Message):
        command = json.JSONDecoder(object_hook=self.object_hook).decode(msg.body)
        self.logger.info(" [x] Received: %s", msg.body)

        try:
            result = command.execute()
            self.cache[command.result] = result
        except Exception as err:
            self.logger.error("Execution of {} failed with error: {}".
                              format(command, err))
            return

        if command.return_result:
            message = amqp.Message(pickle.dumps(result),
                correlation_id=msg.properties["correlation_id"])
            self.channel.basic_publish(message,
                exchange='',
                routing_key=msg.properties["reply_to"]
            )


    def object_hook(self, pairs):
        if 'create' in pairs:
            return Create(**pairs['create'])

        if 'call' in pairs:
            return Call(**pairs['call'])

        if 'get' in pairs:
            return Get(**pairs['get'])

        if '__jsonclass__' in pairs:
            constructor, param = pairs['__jsonclass__']
            if constructor == "Promise":
                return self.cache[param]
            if constructor == "PyObject":
                return pickle.loads(base64.b64decode(param.encode("ascii")))

        return pairs

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M')

    Server().start()
