
from datetime import datetime

def format_unix_timestamp(ts):
    try:
        return datetime.utcfromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M UTC')
    except Exception as e:
        return f"Invalid timestamp: {ts}"

from fastapi import FastAPI, Query
from typing import List
import tls_client
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

def fetch_player_data(player_id):
    try:
        session = tls_client.Session(client_identifier="chrome_120")
        url = f"https://api.sofascore.com/api/v1/player/{player_id}"
        response = session.get(url)
        return {"player_id": player_id, "data": response.json()}
    except Exception as e:
        return {"player_id": player_id, "error": str(e)}

@app.get("/scrape_players")
def scrape_players(player_ids: List[str] = Query(...)):
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_player_data, player_ids))
    return {"results": results}

@app.get("/health")
def health():
    return {"status": "ok"}
@app.get("/scrape_match")
def scrape_match(match_id: str):
    try:
        session = tls_client.Session(client_identifier="chrome_120")
        url = f"https://api.sofascore.com/api/v1/event/{match_id}"
        response = session.get(url)
        return {"match_id": match_id, "data": response.json()}
    except Exception as e:
        return {"match_id": match_id, "error": str(e)}

    except Exception as e:
        return {"match_id": match_id, "error": str(e)}


    except Exception as e:
        return {"match_id": match_id, "error": str(e)}


    except Exception as e:
        return {"match_id": match_id, "error": str(e)}

@app.get("/scrape_match_parsed")
def scrape_match_parsed(match_id: str):
    try:
        session = tls_client.Session(client_identifier="chrome_120")
        url = f"https://api.sofascore.com/api/v1/event/{match_id}"
        response = session.get(url)
        data = response.json()

        event = data.get("event", {})
        home_team = event.get("homeTeam", {})
        away_team = event.get("awayTeam", {})
        home = home_team.get("name", "Home")
        away = away_team.get("name", "Away")
        status = event.get("status", {}).get("description", "Unknown")
        tournament_info = event.get("tournament", {}).get("name", "Unknown Tournament")
        tournament_round = event.get("roundInfo", {}).get("name", "Unknown Round")
        country = event.get("tournament", {}).get("category", {}).get("name", "Unknown Location")
        surface = event.get("groundType", "Unknown Surface")
        court = event.get("venue", {}).get("stadium", {}).get("name", "Unknown Court")
        start_time = event.get("startTimestamp", "Unknown Time")

        set_data = event.get("homeScore", {}).get("periods", [])
        sets = [f"{s.get('home', '-')}-{s.get('away', '-')}" for s in set_data]

        # Serving info
        serving = None
        server_id = event.get("currentServer", {}).get("id")
        if server_id == home_team.get("id"):
            serving = home
        elif server_id == away_team.get("id"):
            serving = away

        # Stats (if present)
        player_stats = {}
        stat_root = event.get("statistics", {}).get("groups", [])
        for group in stat_root:
            for item in group.get("statisticsItems", []):
                name = item.get("name", "")
                home_val = item.get("home", "")
                away_val = item.get("away", "")
                player_stats[name] = {home: home_val, away: away_val}

        # Risk Tag + Tiebreak Detection
        risk_tag = "🟢 Stable"
        tiebreak_flag = any(score in ["6-6", "7-6"] for score in sets)
        if len(sets) >= 2 and sets[0] != sets[1]:
            risk_tag = "🔥 Momentum Shift"
        elif all("0" not in score for score in sets):
            risk_tag = "🛡️ Hold Dominance"
        elif tiebreak_flag:
            risk_tag = "⚠️ Tiebreak Pressure"

        return {
            "match_id": match_id,
            "players": f"{home} vs {away}",
            "tournament": tournament_info or "(Not Provided)",
            "round": tournament_round or "(Not Provided)",
            "location": country if country and country != "Unknown Location" else enrich_tournament_info(event.get("tournament", {}).get("slug", "")).get("location", "(Not Provided)"),
            "court": court or "(Not Provided)",
            "surface": surface if surface and surface != "Unknown Surface" else enrich_tournament_info(event.get("tournament", {}).get("slug", "")).get("surface", "(Not Provided)"),
            "status": status,
            "start_time": format_unix_timestamp(start_time),
            "sets": sets,
            "serving": serving,
            "risk_tag": risk_tag,
            "tiebreak_detected": tiebreak_flag,
            "stats": player_stats,
            "raw": data
        }

    except Exception as e:
        return {"match_id": match_id, "error": str(e)}


import requests
from bs4 import BeautifulSoup

def html_enrich_metadata(match_id):
    try:
        base_url = f"https://www.sofascore.com/tennis/-/{match_id}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(base_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        # Try scraping from meta description or og:title
        meta_desc = soup.find("meta", property="og:description")
        og_title = soup.find("meta", property="og:title")

        tournament = None
        round_name = None
        surface = None

        if og_title and " vs " in og_title.get("content", ""):
            parts = og_title.get("content", "").split(" - ")
            if len(parts) > 1:
                tournament = parts[1].strip()

        if meta_desc:
            desc = meta_desc.get("content", "")
            if "•" in desc:
                fields = [x.strip() for x in desc.split("•")]
                for field in fields:
                    if "Clay" in field or "Hard" in field or "Grass" in field:
                        surface = field
                    elif "Round" in field or "Final" in field:
                        round_name = field

        return {
            "enriched_tournament": tournament,
            "enriched_round": round_name,
            "enriched_surface": surface
        }

    except Exception as e:
        return {"error": str(e)}


# Lookup tables for fallback enrichment
TOURNAMENT_PRESETS = {
    "itf-w15-eindhoven": {"location": "Netherlands", "surface": "Outdoor Clay"},
    "itf-m15-addis-ababa": {"location": "Ethiopia", "surface": "Outdoor Clay"},
    "itf-w15-cairo": {"location": "Egypt", "surface": "Clay"},
    "itf-m15-monastir": {"location": "Tunisia", "surface": "Hard"},
}

def enrich_tournament_info(slug):
    slug = slug.lower().strip()
    return TOURNAMENT_PRESETS.get(slug, {})
