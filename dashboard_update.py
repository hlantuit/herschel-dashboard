import os
from notion_client import Client
from datetime import datetime

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PAGE_ID = os.environ["NOTION_PAGE_ID"]

notion = Client(auth=NOTION_TOKEN)

now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

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
            "rich_text": [{"type": "text", "text": {"content": f"Last update: {now}"}}]
        }
    },
    {
        "object": "block",
        "type": "divider",
        "divider": {}
    },
    {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "🛰 Satellite (Worldview - yesterday)"}}]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{
                "type": "text",
                "text": {
                    "content": "https://worldview.earthdata.nasa.gov/"
                }
            }]
        }
    },
    {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "🌡 Temperature"}}]
        }
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": "To be added: ECCC / Ivvavik station + model blend"}}]
        }
    }
]

# clear page content first (important)
existing_blocks = notion.blocks.children.list(block_id=PAGE_ID)

for b in existing_blocks["results"]:
    notion.blocks.delete(block_id=b["id"])

# push new dashboard
notion.blocks.children.append(
    block_id=PAGE_ID,
    children=blocks
)

print("Dashboard updated")
