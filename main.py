
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
