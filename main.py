import os
import json
import base64
import datetime
import pytz
from twilio.rest import Client
import gspread
from google.oauth2.service_account import Credentials
from urllib.parse import quote

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
        creds = Credentials.from_service_account_info(creds_info, scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ])
        return gspread.authorize(creds)
    except Exception as e:
        print(f"Sheets auth error: {e}")
        return None

def parse_date(raw):
    raw = str(raw).strip()
    # Try all common formats
    for fmt in ('%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%y'):
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except:
            continue
    # Try dateutil as last resort
    try:
        from dateutil import parser as dp
        return dp.parse(raw, dayfirst=True).date()
    except:
        return None

def get_tomorrows_reservations():
    try:
        gc = get_sheets_client()
        if not gc:
            return []
        sheet = gc.open("La Penela Reservations").sheet1
        records = sheet.get_all_records()
        madrid_tz = pytz.timezone('Europe/Madrid')
        tomorrow = (datetime.datetime.now(madrid_tz) + datetime.timedelta(days=1)).date()
        print(f"Looking for reservations on: {tomorrow}")
        results = []
        for r in records:
            raw = r.get('Date', '')
            parsed = parse_date(raw)
            print(f"  Row: {r.get('Name','')} | raw='{raw}' | parsed={parsed} | match={parsed==tomorrow}")
            if parsed and parsed == tomorrow:
                results.append(r)
        return results
    except Exception as e:
        print(f"Sheet error: {e}")
        return []

def make_reminder_call(phone, name, guests, date, time_str):
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        phone_clean = str(phone).strip()
        if not phone_clean.startswith('+'):
            phone_clean = '+' + phone_clean
        webhook_url = f"https://web-production-03008.up.railway.app/confirm-reservation?phone={quote(phone_clean)}&name={quote(str(name))}"
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather numDigits="1" action="{webhook_url}" method="POST" timeout="10">
        <Say language="es-ES" voice="Polly.Conchita">
            Hola {name}, le llamamos de La Penela Moraleja para confirmar su reserva de manana.
            Tiene una mesa para {guests} personas a las {time_str}.
            Pulse 1 para confirmar su reserva.
            Pulse 2 para cancelar.
        </Say>
    </Gather>
    <Say language="es-ES" voice="Polly.Conchita">No hemos recibido respuesta. Por favor llamenos al 9 1 6, 5 0 5, 2 3 2.</Say>
</Response>"""
        call = client.calls.create(
            twiml=twiml,
            to=phone_clean,
            from_=TWILIO_NUMBER
        )
        print(f"Call made to {phone_clean}: {call.sid}")
        return True
    except Exception as e:
        print(f"Call error: {e}")
        return False

def run():
    print(f"Running reminder check at {datetime.datetime.now()}")
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
