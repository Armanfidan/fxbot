import pika


def callback(ch, method, properties, body):
    print(f" [x] Received {body}")


if __name__ == '__main__':
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.basic_consume(queue='candles',
                          auto_ack=True,
                          on_message_callback=callback)
    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()
