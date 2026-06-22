import os
import requests
from datetime import datetime, timedelta
from notion_client import Client

# =========================================================
# AUTH
# =========================================================
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PAGE_ID = os.environ["NOTION_PAGE_ID"]

notion = Client(auth=NOTION_TOKEN)

# =========================================================
# TIME
# =========================================================
now = datetime.utcnow()

# =========================================================
# TEMPERATURE
# =========================================================
def get_temperature():
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 69.590,
            "longitude": -139.099,
            "current_weather": True
        }
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        return {
            "temperature": data["current_weather"]["temperature"],
            "source": "Open-Meteo (ERA5 reanalysis)",
            "status": "ok"
        }
    except Exception as e:
        print("TEMPERATURE FETCH FAILED:", e)
        return {
            "temperature": None,
            "source": "fallback",
            "status": "missing"
        }

temp_data = get_temperature()

temp_text = (
    f"Current air temperature: {temp_data['temperature']} °C\n"
    f"Source: {temp_data['source']}\n"
    f"Status: {temp_data['status']}"
)

# =========================================================
# SATELLITE IMAGE — fetch + validate server-side, then upload
# =========================================================
def build_gibs_url(date_str):
    """
    Build a GIBS WMS 1.1.1 GetMap request.
    Includes VERSION and SRS, which are required — earlier
    version of this script omitted them and GIBS silently
    returned a non-image response.
    """
    bbox = "-141,68,-136,71"  # Herschel Island region

    params = {
        "SERVICE": "WMS",
        "REQUEST": "GetMap",
        "VERSION": "1.1.1",
        "LAYERS": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "STYLES": "",
        "FORMAT": "image/png",
        "TRANSPARENT": "false",
        "WIDTH": "1024",
        "HEIGHT": "768",
        "SRS": "EPSG:4326",
        "BBOX": bbox,
        "TIME": date_str,
    }

    base = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base}?{query}"


def fetch_satellite_image(max_days_back=5):
    """
    Try fetching the GIBS image for today, then walk backwards
    day by day if the response isn't a real PNG (cloud gaps,
    processing delay, no data for that day, etc).

    Returns (image_bytes, date_str_used) or (None, None) if no
    valid image was found in the lookback window.
    """
    for days_back in range(1, max_days_back + 1):
        date_str = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
        url = build_gibs_url(date_str)

        try:
            resp = requests.get(url, timeout=20)
        except Exception as e:
            print(f"GIBS request failed for {date_str}:", e)
            continue

        content_type = resp.headers.get("Content-Type", "")
        print(f"GIBS {date_str}: HTTP {resp.status_code}, Content-Type={content_type}, bytes={len(resp.content)}")

        # Real PNGs start with this magic byte sequence.
        is_real_png = resp.content[:8] == b"\x89PNG\r\n\x1a\n"

        if resp.status_code == 200 and "image/png" in content_type and is_real_png:
            # GIBS sometimes returns a valid PNG that is just a blank/transparent
            # tile (no data for that day). Filter those out by size — a real
            # MODIS true-color tile over land/ice is never this small.
            if len(resp.content) < 5000:
                print(f"  -> rejected: suspiciously small, likely blank tile")
                continue
            return resp.content, date_str
        else:
            print(f"  -> rejected: not a valid PNG response")
            print(f"  -> body preview: {resp.content[:200]}")

    return None, None


satellite_bytes, satellite_date = fetch_satellite_image()

# =========================================================
# UPLOAD IMAGE TO NOTION (file upload, not external URL)
# =========================================================
def upload_image_to_notion(image_bytes, filename="satellite.png"):
    """
    Uses Notion's file upload API so the image is hosted by Notion
    itself, avoiding the external-URL embed problems (no extension,
    unreliable fetch-at-render-time) that caused the image to not
    show up previously.
    """
    create_resp = requests.post(
        "https://api.notion.com/v1/file_uploads",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        json={},
        timeout=20,
    )
    create_resp.raise_for_status()
    upload_id = create_resp.json()["id"]

    send_resp = requests.post(
        f"https://api.notion.com/v1/file_uploads/{upload_id}/send",
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
        },
        files={"file": (filename, image_bytes, "image/png")},
        timeout=30,
    )
    send_resp.raise_for_status()

    return upload_id


satellite_block = None

if satellite_bytes:
    try:
        upload_id = upload_image_to_notion(satellite_bytes)
        satellite_block = {
            "object": "block",
            "type": "image",
            "image": {
                "type": "file_upload",
                "file_upload": {"id": upload_id},
            },
        }
        satellite_caption = f"MODIS Terra true color — {satellite_date}"
    except Exception as e:
        print("NOTION IMAGE UPLOAD FAILED:", e)
        satellite_block = None
        satellite_caption = "Upload to Notion failed — see Action logs"
else:
    satellite_caption = f"No valid satellite image found in the last 5 days (likely cloud cover or processing delay)"

# =========================================================
# DASHBOARD BLOCKS
# =========================================================
blocks = [
    {
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": [{"type": "text", "text": {"content": "Herschel Island Environmental Dashboard"}}]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": f"Last update (UTC): {now.strftime('%Y-%m-%d %H:%M')}"}}]
        }
    },
    {"object": "block", "type": "divider", "divider": {}},

    {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "🛰 Satellite (MODIS True Color)"}}]
        }
    },
]

if satellite_block:
    blocks.append(satellite_block)

blocks.append({
    "object": "block",
    "type": "paragraph",
    "paragraph": {
        "rich_text": [{"type": "text", "text": {"content": satellite_caption}}]
    }
})

blocks += [
    {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "🌡 Air Temperature"}}]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": temp_text}}]
        }
    },
    {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "🧊 Sea Ice Conditions"}}]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": "Next: OSI SAF sea ice concentration integration."}}]
        }
    },
    {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "🌊 Tides & Sea Level"}}]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": "DFO tide gauge (06525) + Copernicus sea level anomaly planned."}}]
        }
    },
]

# =========================================================
# CLEAR PAGE
# =========================================================
existing = notion.blocks.children.list(block_id=PAGE_ID)
print("EXISTING BLOCK COUNT:", len(existing["results"]))

for b in existing["results"]:
    notion.blocks.delete(block_id=b["id"])

# =========================================================
# UPDATE PAGE
# =========================================================
response = notion.blocks.children.append(block_id=PAGE_ID, children=blocks)
print("APPEND RESPONSE BLOCK COUNT:", len(response.get("results", [])))
print("Dashboard updated successfully")
