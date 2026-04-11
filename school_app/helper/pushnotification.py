# helper/pushnotification.py
import os
import json
import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv

load_dotenv()

firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
cred_dict = json.loads(firebase_json)

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

def send_alarm_notification(device_token: str, message: str, slot_time: str) -> bool:
    try:
        msg = messaging.Message(
            notification=messaging.Notification(
                title=f"Alarm — {slot_time}",
                body=message,
            ),
            token=device_token,
        )
        messaging.send(msg)
        print("Successfully sent message:", msg)
        return True
    except Exception as e:
        print("ALARM NOTIFICATION ERROR:", e)
        return False


def send_push_notification(device_token: str, otp: str) -> bool:
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="Login OTP",
                body=f"Your OTP is {otp}"
            ),
            token=device_token
        )
        response = messaging.send(message)
        print("Successfully sent message:", response)
        return True
    except Exception as e:
        print("ERROR:", e)
        return False
