import os, datetime, pytz, gspread
from google.oauth2.service_account import Credentials
from twilio.rest import Client
from dateutil import parser as dateparser

TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")

def get_sheets_client():
    import json, tempfile
    creds_info = json.loads(GOOGLE_CREDS_JSON)
    creds = Credentials.from_service_account_info(creds_info, scopes=['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive'])
    return gspread.authorize(creds)

def get_tomorrows_reservations():
    try:
        gc = get_sheets_client()
        sheet = gc.open("La Penela Reservations").sheet1
        records = sheet.get_all_records()
        madrid_tz = pytz.timezone('Europe/Madrid')
        tomorrow = (datetime.datetime.now(madrid_tz) + datetime.timedelta(days=1)).date()
        results = []
        for r in records:
            raw = str(r.get('Date', '')).strip()
            if not raw:
                continue
            try:
                parsed = dateparser.parse(raw, dayfirst=True).date()
                if parsed == tomorrow:
                    results.append(r)
            except:
                continue
        return results
    except Exception as e:
        print(f"Sheet error: {e}")
        return []

def make_reminder_call(phone, name, guests, date, time_str):
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="es-ES" voice="Polly.Conchita">
        Hola {name}, le llamamos de La Penela Moraleja para confirmar su reserva de mañana.
        Tiene una mesa para {guests} personas a las {time_str}.
        Si necesita cancelar o modificar, llámenos al 9 1 6, 5 0 5, 2 3 2.
        ¡Hasta mañana!
    </Say>
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
