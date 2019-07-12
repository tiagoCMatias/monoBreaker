import pika


class Producer:
    def __init__(self, host, channel):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=channel, durable=True)

    def send_message(self, message, queue):
        self.channel.basic_publish(exchange='',
                                   routing_key=queue,
                                   body=message,
                                   properties=pika.BasicProperties(
                                       delivery_mode=2,  # make message persistent
                                   ))
        print(" [x] Sent {}".format(message))
        self.connection.close()
