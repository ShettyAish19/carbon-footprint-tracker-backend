# backend/app/services/messaging.py
# import os
# import json
# import pika
# from pika.adapters.blocking_connection import BlockingConnection
# from pika.connection import ConnectionParameters

# RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")
# RABBIT_PORT = int(os.getenv("RABBIT_PORT", "5672"))
# RABBIT_USER = os.getenv("RABBIT_USER", "guest")
# RABBIT_PASS = os.getenv("RABBIT_PASS", "guest")
# QUEUE_NAME = os.getenv("RABBIT_QUEUE", "activities")

# def _get_connection_params():
#     credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
#     return ConnectionParameters(host=RABBIT_HOST, port=RABBIT_PORT, credentials=credentials)

# def publish_activity(message: dict) -> bool:
#     """
#     Publish a JSON message to RabbitMQ queue 'activities'.
#     Returns True on success, False on failure.
#     """
  
#     try:
#         params = _get_connection_params()
#         conn = BlockingConnection(params)
#         channel = conn.channel()
#         # durable queue so messages survive broker restart
#         channel.queue_declare(queue=QUEUE_NAME, durable=True)
#         body = json.dumps(message, default=str)
#         channel.basic_publish(
#             exchange='',
#             routing_key=QUEUE_NAME,
#             body=body,
#             properties=pika.BasicProperties(
#                 delivery_mode=2,  # make message persistent
#                 content_type='application/json'
#             )
#         )
#         conn.close()
#         return True
#     except Exception as e:
#         # For dev: print error. In prod: use logging + retry/DLQ
#         print("RabbitMQ publish error:", repr(e))
#         return False

import os
import json
import pika

RABBITMQ_URL = (
    os.getenv("RABBITMQ_PRIVATE_URL")
    or os.getenv("RABBITMQ_URL")  # fallback for local dev
)

def _get_connection_params():
    
    if not RABBITMQ_URL:
        raise RuntimeError("RABBITMQ_URL not set")

    return pika.URLParameters(RABBITMQ_URL)

def publish_activity(payload: dict) -> bool:
    try:
        params = _get_connection_params()
        conn = pika.BlockingConnection(params)
        channel = conn.channel()
        channel.queue_declare(queue="activities", durable=True)
        channel.basic_publish(
            exchange="",
            routing_key="activities",
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        conn.close()
        return True
    except Exception as e:
        print("RabbitMQ publish failed:", e)
        return False
