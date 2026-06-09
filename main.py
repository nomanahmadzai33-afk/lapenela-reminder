import os
import json
import base64
from datetime import datetime, timedelta
from dateutil import parser as dateparser
import pytz
import gspread
from google.oauth2 import service_account
from twilio.rest import Client

# Config
TWILIO_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '+18324301032')
GOOGLE_CREDENTIALS = os.environ.get('GOOGLE_CREDENTIALS')

def get_sheets_client():
    try:
        try:
            creds_info = json.loads(base64.b64decode(GOOGLE_CREDENTIALS).decode())
        except:
            creds_info = json.loads(GOOGLE_CREDENTIALS)
        credentials = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
        return gspread.authorize(credentials)
    except Exception as e:
        print(f"Sheets error: {e}")
        return None

def get_tomorrows_reservations():
    try:
        gc = get_sheets_client()
        sheet = gc.open("La Penela Reservations").sheet1
        records = sheet.get_all_records()
        madrid_tz = pytz.timezone('Europe/Madrid')
        tomorrow = (datetime.now(madrid_tz) + timedelta(days=1)).strftime("%d-%m-%Y")
        results = []
        for r in records:
            if tomorrow in str(r.get('Date', '')) or r.get('Date', '') == tomorrow:
                results.append(r)
        return results
    except Exception as e:
        print(f"Sheet error: {e}")
        return []

def make_reminder_call(phone, name, guests, date, time_str):
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        from urllib.parse import quote
        webhook_url = f"https://web-production-03008.up.railway.app/confirm-reservation?phone={quote(str(phone))}&name={quote(str(name))}"
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather numDigits="1" action="{webhook_url}" method="POST">
        <Say language="es-ES" voice="Polly.Conchita">
            Hola {name}, le llamamos de La Penela Moraleja para confirmar su reserva de mañana.
            Tiene una mesa para {guests} personas a las {time_str}.
            Pulse 1 para confirmar su reserva.
            Pulse 2 para cancelar.
        </Say>
    </Gather>
    <Say language="es-ES" voice="Polly.Conchita">No hemos recibido respuesta. Por favor llámenos al 9 1 6, 5 0 5, 2 3 2.</Say>
</Response>"""
        call = client.calls.create(
            twiml=twiml,
            to=f"+{phone}" if not phone.startswith('+') else phone,
            from_=TWILIO_NUMBER
        )
        print(f"Call made to {phone}: {call.sid}")
        return True
    except Exception as e:
        print(f"Call error: {e}")
        return False

def run():
    print(f"Running reminder check at {datetime.now()}")
    reservations = get_tomorrows_reservations()
    print(f"Found {len(reservations)} reservations for tomorrow")
    for r in reservations:
        name = r.get('Name', '')
        phone = str(r.get('Phone', ''))
        guests = r.get('Guests', '')
        date = r.get('Date', '')
        time_str = r.get('Time', '')
        print(f"Calling {name} at {phone}")
        make_reminder_call(phone, name, guests, date, time_str)

if __name__ == '__main__':
    run()
