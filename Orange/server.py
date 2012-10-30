from amqplib import client_0_8 as amqp

connection = amqp.Connection()
channel = connection.channel()
channel.queue_declare(queue="orange")

def data_received(msg):
    print(" [x] Received: ", msg.body)

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