# helper/pushnotification.py
import os
import json
import firebase_admin
from firebase_admin import credentials, messaging
from dotenv import load_dotenv

load_dotenv()

firebase_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")

if firebase_json and not firebase_admin._apps:
    try:
        cred_dict = json.loads(firebase_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"[Firebase] Init failed: {e}")

def send_alarm_notification(device_token: str, message: str, slot_time: str) -> bool:
    try:
        msg = messaging.Message(
            data={
                "action" : "START_ALARM",
                "title"  : f"Alarm — {slot_time}",
                "message": message,
            },
            android=messaging.AndroidConfig(priority="high"),
            token=device_token,
        )
        response = messaging.send(msg)
        print("Alarm sent successfully. Message ID:", response)
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
