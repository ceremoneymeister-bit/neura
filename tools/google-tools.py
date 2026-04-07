#!/usr/bin/env python3
"""Google Tools for Neura v2 capsules.

CLI wrapper for Google Sheets, Calendar, Drive.
Auto-refreshes tokens using refresh_token.

Usage:
    python3 google-tools.py --home <capsule_home> calendar list [--days 7]
    python3 google-tools.py --home <capsule_home> calendar add "Title" "2026-04-10" ["14:00"] ["15:00"]
    python3 google-tools.py --home <capsule_home> sheets read <spreadsheet_id> [<range>]
    python3 google-tools.py --home <capsule_home> sheets write <spreadsheet_id> <range> '<json_rows>'
    python3 google-tools.py --home <capsule_home> sheets list
    python3 google-tools.py --home <capsule_home> drive list [<query>]
    python3 google-tools.py --home <capsule_home> drive download <file_id> <output_path>
    python3 google-tools.py --home <capsule_home> status
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


# ── Token management ──────────────────────────────────────────────

def find_token(home: str) -> Path:
    """Find Google token file in capsule home."""
    candidates = [
        Path(home) / "data" / "gcal_token.json",
        Path(home) / "data" / "google_token.json",
        Path(home) / "google_token.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return Path(home) / "data" / "google_token.json"  # default path for new tokens


def find_credentials(home: str) -> Path | None:
    """Find Google OAuth client credentials."""
    candidates = [
        Path(home) / "data" / "google_credentials.json",
        Path(home) / "data" / "credentials.json",
        Path(home) / "data" / "legacy" / "credentials.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_creds(home: str, scopes: list[str] | None = None) -> Credentials:
    """Load and refresh Google credentials."""
    token_path = find_token(home)
    if not token_path.exists():
        print(f"ERROR: No Google token found. User needs to run /connect_google first.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(token_path.read_text())
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=scopes or data.get("scopes", []),
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token
            data["token"] = creds.token
            data["expiry"] = creds.expiry.isoformat() if creds.expiry else None
            if scopes:
                data["scopes"] = scopes
            token_path.write_text(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            print(f"ERROR: Token refresh failed: {e}", file=sys.stderr)
            print("User may need to re-authorize via /connect_google", file=sys.stderr)
            sys.exit(1)

    return creds


# ── Calendar ──────────────────────────────────────────────────────

def calendar_list(home: str, days: int = 7):
    """List upcoming calendar events."""
    creds = load_creds(home, scopes=["https://www.googleapis.com/auth/calendar"])
    service = build("calendar", "v3", credentials=creds)

    now = datetime.now(timezone.utc).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

    result = service.events().list(
        calendarId="primary",
        timeMin=now,
        timeMax=end,
        maxResults=50,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = result.get("items", [])
    if not events:
        print(f"Нет событий в ближайшие {days} дней.")
        return

    print(f"📅 События на {days} дней ({len(events)}):\n")
    for ev in events:
        start = ev["start"].get("dateTime", ev["start"].get("date", ""))
        summary = ev.get("summary", "(без названия)")
        location = ev.get("location", "")
        if "T" in start:
            dt = datetime.fromisoformat(start)
            time_str = dt.strftime("%d.%m %H:%M")
        else:
            time_str = start
        line = f"  • {time_str} — {summary}"
        if location:
            line += f" 📍 {location}"
        print(line)


def calendar_add(home: str, title: str, date: str, start_time: str = None, end_time: str = None):
    """Add a calendar event."""
    creds = load_creds(home, scopes=["https://www.googleapis.com/auth/calendar"])
    service = build("calendar", "v3", credentials=creds)

    if start_time:
        start_dt = f"{date}T{start_time}:00"
        if end_time:
            end_dt = f"{date}T{end_time}:00"
        else:
            # Default 1 hour duration
            from datetime import datetime as _dt
            s = _dt.fromisoformat(start_dt)
            e = s + timedelta(hours=1)
            end_dt = e.isoformat()
        event = {
            "summary": title,
            "start": {"dateTime": start_dt, "timeZone": "Europe/Moscow"},
            "end": {"dateTime": end_dt, "timeZone": "Europe/Moscow"},
        }
    else:
        event = {
            "summary": title,
            "start": {"date": date},
            "end": {"date": date},
        }

    result = service.events().insert(calendarId="primary", body=event).execute()
    print(f"✅ Событие создано: {title}")
    print(f"   Дата: {date}" + (f" {start_time}" if start_time else ""))
    print(f"   ID: {result.get('id')}")
    print(f"   Ссылка: {result.get('htmlLink', 'N/A')}")


# ── Sheets ────────────────────────────────────────────────────────

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def sheets_list(home: str):
    """List recent spreadsheets."""
    creds = load_creds(home, scopes=SHEETS_SCOPES)
    service = build("drive", "v3", credentials=creds)

    result = service.files().list(
        q="mimeType='application/vnd.google-apps.spreadsheet'",
        pageSize=20,
        orderBy="modifiedTime desc",
        fields="files(id, name, modifiedTime)",
    ).execute()

    files = result.get("files", [])
    if not files:
        print("Нет таблиц в Google Drive.")
        return

    print(f"📊 Таблицы ({len(files)}):\n")
    for f in files:
        mod = f.get("modifiedTime", "")[:10]
        print(f"  • {f['name']}")
        print(f"    ID: {f['id']}  (изменён: {mod})")


def sheets_read(home: str, spreadsheet_id: str, range_: str = "A1:Z100"):
    """Read data from a spreadsheet."""
    creds = load_creds(home, scopes=SHEETS_SCOPES)
    service = build("sheets", "v4", credentials=creds)

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_,
    ).execute()

    values = result.get("values", [])
    if not values:
        print("Пустой диапазон.")
        return

    # Print as table
    print(f"📊 {range_} ({len(values)} строк):\n")
    for i, row in enumerate(values):
        if i == 0:
            print(" | ".join(str(c) for c in row))
            print("-" * 60)
        else:
            print(" | ".join(str(c) for c in row))


def sheets_write(home: str, spreadsheet_id: str, range_: str, data_json: str):
    """Write data to a spreadsheet."""
    creds = load_creds(home, scopes=SHEETS_SCOPES)
    service = build("sheets", "v4", credentials=creds)

    rows = json.loads(data_json)
    body = {"values": rows}

    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()

    print(f"✅ Записано: {result.get('updatedCells', 0)} ячеек в {range_}")


# ── Drive ─────────────────────────────────────────────────────────

def drive_list(home: str, query: str = None):
    """List files in Google Drive."""
    creds = load_creds(home, scopes=["https://www.googleapis.com/auth/drive.readonly"])
    service = build("drive", "v3", credentials=creds)

    q = query if query else None
    result = service.files().list(
        q=q,
        pageSize=20,
        orderBy="modifiedTime desc",
        fields="files(id, name, mimeType, modifiedTime, size)",
    ).execute()

    files = result.get("files", [])
    if not files:
        print("Файлов не найдено.")
        return

    print(f"📁 Файлы ({len(files)}):\n")
    for f in files:
        mod = f.get("modifiedTime", "")[:10]
        size = f.get("size", "")
        size_str = f" ({int(size)//1024}KB)" if size else ""
        print(f"  • {f['name']}{size_str}")
        print(f"    ID: {f['id']}  Type: {f.get('mimeType', '?')}  ({mod})")


def drive_download(home: str, file_id: str, output_path: str):
    """Download a file from Google Drive."""
    import io
    creds = load_creds(home, scopes=["https://www.googleapis.com/auth/drive.readonly"])
    service = build("drive", "v3", credentials=creds)

    request = service.files().get_media(fileId=file_id)
    with open(output_path, "wb") as f:
        downloader = MediaIoBaseDownload(io.FileIO(f.name, "wb"), request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    size = os.path.getsize(output_path)
    print(f"✅ Скачан: {output_path} ({size // 1024}KB)")


# ── Status ────────────────────────────────────────────────────────

def show_status(home: str):
    """Show Google integration status."""
    token_path = find_token(home)
    creds_path = find_credentials(home)

    print("🔗 Google Integration Status\n")
    print(f"  Token:       {'✅ ' + str(token_path) if token_path.exists() else '❌ Not found'}")
    print(f"  Credentials: {'✅ ' + str(creds_path) if creds_path else '❌ Not found'}")

    if token_path.exists():
        data = json.loads(token_path.read_text())
        scopes = data.get("scopes", [])
        expiry = data.get("expiry", "N/A")
        has_refresh = bool(data.get("refresh_token"))
        print(f"  Refresh:     {'✅ Present' if has_refresh else '❌ Missing'}")
        print(f"  Expiry:      {expiry}")
        print(f"  Scopes:      {', '.join(s.split('/')[-1] for s in scopes)}")

        # Try refresh
        try:
            creds = load_creds(home)
            print(f"  Connection:  ✅ Working (token refreshed)")
        except SystemExit:
            print(f"  Connection:  ❌ Failed to refresh")
        except Exception as e:
            print(f"  Connection:  ❌ Error: {e}")


# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Google Tools for Neura capsules")
    parser.add_argument("--home", required=True, help="Capsule home directory")
    sub = parser.add_subparsers(dest="service")

    # Calendar
    cal = sub.add_parser("calendar")
    cal_sub = cal.add_subparsers(dest="action")
    cal_list = cal_sub.add_parser("list")
    cal_list.add_argument("--days", type=int, default=7)
    cal_add = cal_sub.add_parser("add")
    cal_add.add_argument("title")
    cal_add.add_argument("date", help="YYYY-MM-DD")
    cal_add.add_argument("start_time", nargs="?", help="HH:MM")
    cal_add.add_argument("end_time", nargs="?", help="HH:MM")

    # Sheets
    sh = sub.add_parser("sheets")
    sh_sub = sh.add_subparsers(dest="action")
    sh_sub.add_parser("list")
    sh_read = sh_sub.add_parser("read")
    sh_read.add_argument("spreadsheet_id")
    sh_read.add_argument("range", nargs="?", default="A1:Z100")
    sh_write = sh_sub.add_parser("write")
    sh_write.add_argument("spreadsheet_id")
    sh_write.add_argument("range")
    sh_write.add_argument("data", help="JSON array of rows")

    # Drive
    dr = sub.add_parser("drive")
    dr_sub = dr.add_subparsers(dest="action")
    dr_list = dr_sub.add_parser("list")
    dr_list.add_argument("query", nargs="?")
    dr_dl = dr_sub.add_parser("download")
    dr_dl.add_argument("file_id")
    dr_dl.add_argument("output_path")

    # Status
    sub.add_parser("status")

    args = parser.parse_args()

    if not args.service:
        parser.print_help()
        sys.exit(1)

    home = args.home

    if args.service == "status":
        show_status(home)
    elif args.service == "calendar":
        if args.action == "list":
            calendar_list(home, days=args.days)
        elif args.action == "add":
            calendar_add(home, args.title, args.date, args.start_time, args.end_time)
        else:
            cal.print_help()
    elif args.service == "sheets":
        if args.action == "list":
            sheets_list(home)
        elif args.action == "read":
            sheets_read(home, args.spreadsheet_id, args.range)
        elif args.action == "write":
            sheets_write(home, args.spreadsheet_id, args.range, args.data)
        else:
            sh.print_help()
    elif args.service == "drive":
        if args.action == "list":
            drive_list(home, args.query)
        elif args.action == "download":
            drive_download(home, args.file_id, args.output_path)
        else:
            dr.print_help()


if __name__ == "__main__":
    main()
