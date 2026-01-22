# backend/consumer.py
import os
import json
import time
import traceback
from app.services.messaging import _get_connection_params
import pika
from app.db.session import SessionLocal, init_db
from app.db.crud import create_suggestion, delete_fallback_suggestions_for_activity
from app.services.ai_service import generate_suggestions_for_activity
from sqlalchemy.orm import Session
from app.services.gamification import update_user_stats

from dotenv import load_dotenv
load_dotenv()
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

print("DEBUG CONSUMER GEMINI:", bool(os.getenv("GEMINI_API_KEY")))
print("DEBUG CONSUMER CLIMATIQ:", bool(os.getenv("CLIMATIQ_API_KEY")))

init_db()

QUEUE = os.getenv("RABBIT_QUEUE", "activities")
params = _get_connection_params()

def handle_message(body: bytes):
    try:
        data = json.loads(body)
        user_id = data.get("user_id")
        activity_id = data.get("activity_id")

        suggestions = generate_suggestions_for_activity(data)
        db: Session = SessionLocal()

        # Remove fallback suggestions
        try:
            delete_fallback_suggestions_for_activity(db, activity_id)
        except Exception as e:
            print("Warning: could not delete fallback suggestions:", e)

        # Insert AI suggestions
        for s in suggestions:
            create_suggestion(
                db,
                user_id=user_id,
                activity_id=activity_id,
                text=s.get("text"),
                est_saving=s.get("est_saving_kg"),
                difficulty=s.get("difficulty"),
                meta=s,
                source="ai"
            )

        # ✅ GAMIFICATION UPDATE (critical)
        update_user_stats(db, user_id)

        db.close()
        return True

    except Exception as e:
        print("Error handling message:", e)
        traceback.print_exc()
        return False


def consume():
    conn = pika.BlockingConnection(params)
    channel = conn.channel()
    channel.queue_declare(queue=QUEUE, durable=True)
    def callback(ch, method, properties, body):
        ok = handle_message(body)
        if ok:
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE, on_message_callback=callback)
    print("Consumer started. Waiting for messages...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Stopping consumer...")
        channel.stop_consuming()
    conn.close()

if __name__ == "__main__":
    consume()
