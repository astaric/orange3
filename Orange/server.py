from amqplib import client_0_8 as amqp
import json, pickle
import importlib
import base64
import logging

class Command:
    result = None

    def __init__(self, **params):
        for n, v in params.items():
            if not hasattr(self, n):
                logging.error(params.items())
                raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, n))
            setattr(self, n, v)

class Create(Command):
    module = ""
    class_ = ""
    args   = ()
    kwargs = {}

class Call(Command):
    object = ""
    method = ""
    args   = ()
    kwargs = {}

class Get(Command):
    object = ""
    member = ""

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
        request = json.JSONDecoder(object_hook=self.object_hook).decode(msg.body)
        self.logger.info(" [x] Received: %s", msg.body)

        if isinstance(request, Create):
            module = importlib.import_module(request.module)
            cls = getattr(module, request.class_)
            try:
                obj = cls(*request.args, **request.kwargs)
                self.cache[request.result] = obj
            except Exception as err:
                self.logger.error("Call to %s(*%s, **%s) failed (%s).",
                                  request.class_, request.args, request.kwargs, err)
        elif isinstance(request, Call):
            try:
                obj = self.cache[request.object]
                result = getattr(obj, request.method)(*request.args, **request.kwargs)
                self.cache[request.result] = result
                self.logger.debug("Returned %s", result)
            except KeyError:
                self.logger.error('I have never heard of object %s', request.object)
            except Exception as err:
                self.logger.error("Call to %s.%s(*%s, **%s) failed. (%s)",
                    obj.__class__.__name__, request.method, request.args, request.kwargs, err)

        elif isinstance(request, Get):
            try:
                obj = self.cache[request.object]
                if request.member == '':
                    message = amqp.Message(pickle.dumps(obj),
                                           correlation_id=msg.properties["correlation_id"])
                    self.channel.basic_publish(message,
                        exchange='',
                        routing_key=msg.properties["reply_to"]
                    )
                else:
                    result = getattr(obj, request.member)
                    self.cache[request.result] = result
                    self.logger.debug("Returned %s", result)
            except KeyError:
                self.logger.error("Getting of object %s failed, no such object exists.", request.object)


    def object_hook(self, pairs):
        if 'create' in pairs:
            return Create(**pairs['create'])

        if 'call' in pairs:
            return Call(**pairs['call'])

        if 'get' in pairs:
            return Get(**pairs['get'])

        if '__jsonclass__' in pairs:
            constructor, param = pairs['__jsonclass__']
            if constructor == "Proxy":
                return self.cache[param]
            if constructor == "PyObject":
                return pickle.loads(base64.b64decode(param.encode("ascii")))

        return pairs

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M')

    Server().start()
