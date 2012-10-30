from amqplib import client_0_8 as amqp
import json, pickle
import importlib

class Proxy:
    __id__ = None

    def __init__(self, id):
        self.__id__ = id

def object_hook(pairs):
    if '__jsonclass__' in pairs:
        constructor, id = pairs['__jsonclass__']
        print(constructor, id)
        if constructor == "Proxy":
            return cache[id]
    return pairs

class ProxyDecoder(json.JSONDecoder):
    def __init__(self, **kwargs):
        if not kwargs.get('object_hook'):
            kwargs['object_hook'] = object_hook
        super().__init__(**kwargs)



connection = amqp.Connection()
channel = connection.channel()
channel.queue_declare(queue="orange")


cache = {}
def data_received(msg : amqp.Message):
    request = ProxyDecoder().decode(msg.body)
    print(" [x] Received: ", msg.body)
    if request["method"] == "__new__":
        module = importlib.import_module(request["module"])
        cls = getattr(module, request["class"])
        try:
            obj = cls(*request["args"], **request["kwargs"])
            cache[request["result"]] = obj
            print("Created object %s" % obj)
        except Exception as er:
            print("[ERROR] Call to %s(*%s, **%s) failed (%s)." % (request["class"], request["args"], request["kwargs"], er))
    elif request["method"] == "__get__":
        try:
            obj = cache[request["object"]]
            message = amqp.Message(pickle.dumps(obj),
                correlation_id=msg.properties["correlation_id"])
            channel.basic_publish(message,
                exchange='',
                routing_key=msg.properties["reply_to"]
            )

        except KeyError:
            print("[ERROR] Getting of object %s failed, no such object exists." % request["object"])


    else:
        obj = cache[request["object"]]
        try:
            result = getattr(obj, request["method"])(*request["args"], **request["kwargs"])
            cache[request["result"]] = result
            print("Returned %s" % result)
        except:
            print("[ERROR] Call to %s.%s(*%s, **%s) failed." % (obj.__class__.__name__, request["method"], request["args"], request["kwargs"]))



channel.basic_consume(queue="orange", callback=data_received)

print(" [*] Waiting for messages. To exit press CTRL+C")

try:
    while True:
        channel.wait()
except KeyboardInterrupt:
    pass

print(" [*] Closing connection")
channel.close()
connection.close()