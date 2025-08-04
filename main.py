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
@app.get("/scrape_match_parsed")
def scrape_match_parsed(match_id: str):
    try:
        session = tls_client.Session(client_identifier="chrome_120")
        url = f"https://api.sofascore.com/api/v1/event/{match_id}"
        response = session.get(url)
        data = response.json()

        event = data.get("event", {})
        home = event.get("homeTeam", {}).get("name", "Home")
        away = event.get("awayTeam", {}).get("name", "Away")
        status = event.get("status", {}).get("description", "Unknown")
        tournament = event.get("tournament", {}).get("name", "Unknown Tournament")

        sets = []
        scores = event.get("homeScore", {}).get("period1", {}), event.get("awayScore", {}).get("period1", {})
        set_data = event.get("homeScore", {}).get("periods", [])
        for s in set_data:
            home_score = s.get("home", "-")
            away_score = s.get("away", "-")
            sets.append(f"{home_score}-{away_score}")

        return {
            "match_id": match_id,
            "players": f"{home} vs {away}",
            "status": status,
            "tournament": tournament,
            "sets": sets,
            "raw": data
        }

    except Exception as e:
        return {"match_id": match_id, "error": str(e)}
