#!/usr/bin/env python3
""" 
Jeeves — Morning Briefing Printer
Fetches weather, calendar and news, generates a briefing via Ollama,
and prints it on the GB01 cat printer over BLE.
"""

import asyncio
import json
import os
import datetime
import requests
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

# Google Calendar
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# BLE printer
from bleak import BleakClient, BleakScanner

# ─────────────────────────────────────────────
# CONFIGURATION — edit these
# ─────────────────────────────────────────────

TIMEZONE         = "Europe/London"
LATITUDE         = 52.5072      #  change to your location
LONGITUDE        = -0.1276

NEWS_RSS_URL     = "http://feeds.bbci.co.uk/news/rss.xml"
NEWS_HEADLINE_COUNT = 3

OLLAMA_URL       = "http://localhost:11434/api/generate"
OLLAMA_MODEL     = "llama3.2:3b"

# GB01 BLE details — will auto-scan if MAC left blank
# PRINTER_MAC      = ""           # e.g. "AA:BB:CC:DD:EE:FF" — fill in after first run
PRINTER_CHAR_UUID = "XXXXXX"

GOOGLE_CREDS_FILE = os.path.expanduser("credentials.json")
GOOGLE_TOKEN_FILE = os.path.expanduser("token.json")
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


# ─────────────────────────────────────────────
# WEATHER  (Open-Meteo, no API key needed)
# ─────────────────────────────────────────────

def get_weather():
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={LATITUDE}&longitude={LONGITUDE}"
            f"&current=temperature_2m,weathercode,windspeed_10m"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&timezone={TIMEZONE.replace('/', '%2F')}&forecast_days=1"
        )
        data = requests.get(url, timeout=10).json()
        current = data["current"]
        daily   = data["daily"]

        code  = current["weathercode"]
        temp  = current["temperature_2m"]
        wind  = current["windspeed_10m"]
        hi    = daily["temperature_2m_max"][0]
        lo    = daily["temperature_2m_min"][0]
        rain  = daily["precipitation_sum"][0]

        # Simple weather code mapping
        descriptions = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Drizzle",
            55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
            71: "Light snow", 73: "Snow", 75: "Heavy snow",
            80: "Rain showers", 81: "Showers", 82: "Heavy showers",
            95: "Thunderstorm"
        }
        desc = descriptions.get(code, "Mixed conditions")

        return (
            f"{desc}, {temp:.0f}C now. "
            f"High {hi:.0f}C, low {lo:.0f}C. "
            f"Wind {wind:.0f}km/h. "
            f"Rain {rain:.1f}mm expected."
        )
    except Exception as e:
        return f"Weather unavailable ({e})"


# ─────────────────────────────────────────────
# GOOGLE CALENDAR
# ─────────────────────────────────────────────

def get_calendar_events():
    try:
        creds = None
        if os.path.exists(GOOGLE_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(GOOGLE_TOKEN_FILE, "w") as f:
                    f.write(creds.to_json())
            else:
                # First run only — requires interactive browser auth
                # Run this script manually once to generate token.json
                flow = InstalledAppFlow.from_client_secrets_file(
                    GOOGLE_CREDS_FILE, SCOPES
                )
                #creds = flow.run_local_server(port=0)
                creds = flow.run_local_server(port=0)
                with open(GOOGLE_TOKEN_FILE, "w") as f:
                    f.write(creds.to_json())

        service = build("calendar", "v3", credentials=creds)

        tz   = ZoneInfo(TIMEZONE)
        now  = datetime.datetime.now(tz)
        eod  = now.replace(hour=23, minute=59, second=59)

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=eod.isoformat(),
            maxResults=10,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return "No events today."

        lines = []
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date", ""))
            if "T" in start:
                time_str = datetime.datetime.fromisoformat(start).strftime("%H:%M")
            else:
                time_str = "All day"
            title = e.get("summary", "Untitled")
            lines.append(f"{time_str} {title}")

        return "\n".join(lines)

    except Exception as ex:
        return f"Calendar unavailable ({ex})"


# ─────────────────────────────────────────────
# NEWS HEADLINES  (BBC RSS)
# ─────────────────────────────────────────────

def get_news():
    try:
        response = requests.get(NEWS_RSS_URL, timeout=10)
        root     = ET.fromstring(response.content)
        items    = root.findall(".//item")[:NEWS_HEADLINE_COUNT]
        headlines = [item.find("title").text for item in items if item.find("title") is not None]
        return "\n".join(f"- {h}" for h in headlines)
    except Exception as e:
        return f"News unavailable ({e})"


# ─────────────────────────────────────────────
# OLLAMA  — generate the briefing paragraph
# ─────────────────────────────────────────────

def generate_briefing(weather, calendar, news):
    today = datetime.datetime.now(ZoneInfo(TIMEZONE)).strftime("%A %d %B %Y")
    prompt = f"""You are Jeeves, an extremely concise, literal, and efficient butler. 
Provide a fast morning briefing for your employer. Today is {today}.

STRICT DATA:
[WEATHER]: {weather}
[CALENDAR]: {calendar}
[NEWS]: {news}

STRICT INSTRUCTIONS:
1. Maximum length: 3 sentences. Keep it incredibly brief.
2. DO NOT mix the sections. The Calendar is personal schedule. The News is external world events. 
3. State the weather clearly and suggest one practical action if required
4. Mention everything on the calendar
5. NEVER mix calendar events and news
4. No pleasantries, no asking questions, no offering tea. Just the facts in paragraph form.."""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120
        )
        return response.json()["response"].strip()
    except Exception as e:
        return f"Good morning. Briefing unavailable today ({e})."


# ─────────────────────────────────────────────
# FIND PRINTER  — scan if MAC not set
# ─────────────────────────────────────────────


async def find_printer_mac():
    print("Setting the Proximity Trap for Jeeves...")
    print("Make sure the printer is right next to the Pi, then turn it ON.")

    # Filter by physics (signal strength), completely ignoring names and UUIDs!
    found_device = await BleakScanner.find_device_by_filter(
        lambda d, ad: ad.rssi > -40,
        timeout=20.0
    )

    if found_device:
        print(f"Gotcha! Snagged device with burner MAC: {found_device.address}")
        return found_device.address
    else:
        print("Trap empty. Printer not found. Make sure it's turned on and flashing.")
        return None



# ─────────────────────────────────────────────
# PRINT  — send to GB01 over BLE GATT
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

async def main():
    print("Jeeves is preparing your morning briefing...\n")

    # Gather data
    print("Fetching weather...")
    weather  = get_weather()
    print(f"  {weather}\n")

    print("Fetching calendar...")
    calendar = get_calendar_events()
    print(f"  {calendar}\n")

    print("Fetching news...")
    news     = get_news()
    print(f"  {news}\n")

    # Generate briefing
    print("Generating briefing via Ollama (this may take 30-60 seconds)...")
    briefing = generate_briefing(weather, calendar, news)
    print(f"\nBriefing:\n{briefing}\n")

    print("saving briefing to jeeves_output.txt")
    with open("jeeves_output.txt", "w", encoding="utf-8") as f:
         f.write(briefing)

    print("\nHanding off to the print spooler")

    # The proper, async way to run a terminal command
    process = await asyncio.create_subprocess_shell(
        "sudo python gb01print.py --assume-text jeeves_output.txt"
    )
    
    # Await the process to finish before Jeeves officially clocks out
    await process.communicate()

if __name__ == "__main__":
    asyncio.run(main())
