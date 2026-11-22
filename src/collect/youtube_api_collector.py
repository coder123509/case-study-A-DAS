"""
YouTube Data API v3 collector (official API, needs a free key).

1) video statistics for our trailer IDs      -> data/raw/youtube/youtube_api_videos_<timestamp>.json  (raw API JSON)
2) top-level comments for the chosen trailers -> data/raw/youtube_comments/comments_<video>_<timestamp>.csv
   (author names / channel ids are NOT saved - assignment privacy rule)

Setup:
    1. Google Cloud console -> new project -> enable "YouTube Data API v3" -> create an API key
    2. set the key in your shell (never commit it!):
          Windows PowerShell:  $env:YT_API_KEY="your_key"
          mac / linux:         export YT_API_KEY=your_key
    3. python src/collect/youtube_api_collector.py              (stats only)
       python src/collect/youtube_api_collector.py --comments   (stats + comments, ~1 quota unit per 100 comments)

Running it once a day gives you REAL daily snapshots (velocity!) instead of one cumulative counter.
Free quota is 10,000 units/day; videos.list = 1 unit, commentThreads.list = 1 unit per page of 100.
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
API = "https://www.googleapis.com/youtube/v3"

# video id -> film key (same IDs as data/raw/youtube/youtube_trailers_snapshot_2026-11-21.json)
VIDEOS = {
    "hA6hldpSTF8": "AVG_ENDGAME_2019", "XwYnB6eBWTc": "AVG_ENDGAME_2019", "TcMBFSGVi1c": "AVG_ENDGAME_2019",
    "LPhqL4DqzBg": "AVG_ENDGAME_2019", "KCSNFZKbhZE": "AVG_ENDGAME_2019",
    "L2NAh3CIdig": "AVG_ENCORE_2026", "gq01MdYW120": "AVG_ENCORE_2026",
    "UiMg566PREA": "AVG_DOOMSDAY_2026", "1clWprLC5Ak": "AVG_DOOMSDAY_2026", "kH1XlwHQv9o": "AVG_DOOMSDAY_2026",
    "399Ez7WHK5s": "AVG_DOOMSDAY_2026", "irVNGjRFZGk": "AVG_DOOMSDAY_2026", "hvKW6iDOZrc": "AVG_DOOMSDAY_2026",
    "X1aFkAkFASk": "AVG_DOOMSDAY_2026", "UfNu7pcR0e8": "AVG_DOOMSDAY_2026", "Fg0jyss_YnU": "AVG_DOOMSDAY_2026",
}
# comments: the two official trailers per film + the Hindi ones (Indian audience)
COMMENT_VIDEOS = ["hA6hldpSTF8", "LPhqL4DqzBg", "irVNGjRFZGk", "hvKW6iDOZrc"]
MAX_COMMENTS_PER_VIDEO = 5000


def get(endpoint, **params):
    params["key"] = os.environ["YT_API_KEY"]
    r = requests.get(f"{API}/{endpoint}", params=params, timeout=30)
    if r.status_code == 403:
        raise SystemExit(f"403 from YouTube: {r.json().get('error', {}).get('message')}")
    r.raise_for_status()
    return r.json()


def collect_stats(stamp):
    js = get("videos", part="snippet,statistics,contentDetails", id=",".join(VIDEOS), maxResults=50)
    out = ROOT / "data" / "raw" / "youtube" / f"youtube_api_videos_{stamp}.json"
    js["_collected_at_utc"] = stamp
    out.write_text(json.dumps(js, indent=2, ensure_ascii=False), encoding="utf-8")
    print("saved", out.name, len(js.get("items", [])), "videos")


def collect_comments(video_id, stamp):
    out = ROOT / "data" / "raw" / "youtube_comments" / f"comments_{video_id}_{stamp}.csv"
    n, token = 0, None
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["film_key", "video_id", "comment_id", "published_at", "updated_at", "like_count", "reply_count", "text"])
        while n < MAX_COMMENTS_PER_VIDEO:
            js = get("commentThreads", part="snippet", videoId=video_id, maxResults=100, order="time",
                     textFormat="plainText", pageToken=token or "")
            for it in js.get("items", []):
                top = it["snippet"]["topLevelComment"]
                s = top["snippet"]
                # authorDisplayName / authorChannelId deliberately not written
                w.writerow([VIDEOS[video_id], video_id, top["id"], s["publishedAt"], s["updatedAt"],
                            s.get("likeCount", 0), it["snippet"].get("totalReplyCount", 0), s["textDisplay"]])
                n += 1
            token = js.get("nextPageToken")
            if not token:
                break
            time.sleep(0.2)
    print("saved", out.name, n, "comments")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--comments", action="store_true")
    args = ap.parse_args()
    if "YT_API_KEY" not in os.environ:
        raise SystemExit("Set YT_API_KEY first (see the docstring at the top of this file).")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
    collect_stats(stamp)
    if args.comments:
        for vid in COMMENT_VIDEOS:
            collect_comments(vid, stamp)
