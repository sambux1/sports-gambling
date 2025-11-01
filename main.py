TEAMS = [
    {"abbr": "ari", "name": "Arizona Cardinals"},
    {"abbr": "atl", "name": "Atlanta Falcons"},
    {"abbr": "bal", "name": "Baltimore Ravens"},
    {"abbr": "buf", "name": "Buffalo Bills"},
    {"abbr": "car", "name": "Carolina Panthers"},
    {"abbr": "chi", "name": "Chicago Bears"},
    {"abbr": "cin", "name": "Cincinnati Bengals"},
    {"abbr": "cle", "name": "Cleveland Browns"},
    {"abbr": "dal", "name": "Dallas Cowboys"},
    {"abbr": "den", "name": "Denver Broncos"},
    {"abbr": "det", "name": "Detroit Lions"},
    {"abbr": "gb", "name": "Green Bay Packers"},
    {"abbr": "hou", "name": "Houston Texans"},
    {"abbr": "ind", "name": "Indianapolis Colts"},
    {"abbr": "jax", "name": "Jacksonville Jaguars"},
    {"abbr": "kc", "name": "Kansas City Chiefs"},
    {"abbr": "lv", "name": "Las Vegas Raiders"},
    {"abbr": "lar", "name": "Los Angeles Rams"},
    {"abbr": "lac", "name": "Los Angeles Chargers"},
    {"abbr": "mia", "name": "Miami Dolphins"},
    {"abbr": "min", "name": "Minnesota Vikings"},
    {"abbr": "ne", "name": "New England Patriots"},
    {"abbr": "no", "name": "New Orleans Saints"},
    {"abbr": "nyg", "name": "New York Giants"},
    {"abbr": "nyj", "name": "New York Jets"},
    {"abbr": "phi", "name": "Philadelphia Eagles"},
    {"abbr": "pit", "name": "Pittsburgh Steelers"},
    {"abbr": "sf", "name": "San Francisco 49ers"},
    {"abbr": "sea", "name": "Seattle Seahawks"},
    {"abbr": "tb", "name": "Tampa Bay Buccaneers"},
    {"abbr": "ten", "name": "Tennessee Titans"},
    {"abbr": "wsh", "name": "Washington Commanders"},
]

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import requests
import json

ODDS_API_HOST = "https://api.the-odds-api.com"
NFL_SPORT_KEY = "americanfootball_nfl"


# load the api key from .api-keys.json
def get_api_key() -> str:
    with open(".api-keys.json", "r") as f:
        data = json.load(f)
    return data.get("the_odds_api")

# convert a datetime to iso format
def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def find_next_game(
    api_key: str,
    team_abbr: str,
    window_days: int = 4,
    sport_key: str = NFL_SPORT_KEY,
) -> Optional[Dict[str, Any]]:
    """
    Find the next scheduled game for the given team within the given window.

    Returns the event object (including id, commence_time, home_team, away_team) or None.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=12)  # include slight lookback for scheduling quirks
    end = now + timedelta(days=window_days)

    url = f"{ODDS_API_HOST}/v4/sports/{NFL_SPORT_KEY}/events"
    params = {
        "apiKey": api_key,
        "dateFormat": "iso",
        "commenceTimeFrom": _iso(start),
        "commenceTimeTo": _iso(end),
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    events: List[Dict[str, Any]] = resp.json() or []

    team_name = next((t["name"] for t in TEAMS if t["abbr"] == team_abbr), None)
    if not team_name:
        raise ValueError(f"Team abbreviation {team_abbr} not found")

    events = [
        e
        for e in events
        if e.get("home_team") == team_name or e.get("away_team") == team_name
    ]
    if not events:
        return None

    events.sort(key=lambda e: e.get("commence_time", ""))
    return events[0]

def fetch_event_player_pass_yds(
    api_key: str,
    event_id: str,
    regions: str = "us",
    odds_format: str = "american",
) -> List[Dict[str, Any]]:
    """
    Fetch bookmakers' markets for player passing yards for a specific event.

    Returns a list of bookmaker dicts with embedded markets/outcomes.
    """
    url = f"{ODDS_API_HOST}/v4/sports/{NFL_SPORT_KEY}/events/{event_id}/odds"
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": "player_pass_yds",
        "oddsFormat": odds_format,
        "dateFormat": "iso",
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data: Dict[str, Any] = resp.json() or {}
    return data.get("bookmakers", []), resp.headers

def extract_qb_ou(
    bookmakers: List[Dict[str, Any]],
    qb_name: str,
) -> List[Tuple[str, Optional[float], Optional[int], Optional[int]]]:
    """
    Extract the Over/Under line and prices per bookmaker for the two QBs in a given event.

    Returns list of tuples: (bookmaker_title, line_point, over_price, under_price)
    If a bookmaker has no QB market, the tuple will contain None values for line/prices.
    """
    results: List[Tuple[str, Optional[float], Optional[int], Optional[int]]] = []
    market_key = "player_pass_yds"

    for book in bookmakers:
        title = book.get("title") or book.get("key", "unknown")
        line_point: Optional[float] = None
        over_price: Optional[int] = None
        under_price: Optional[int] = None

        for m in book.get("markets", []):
            if m.get("key") != market_key:
                continue
            outcomes = m.get("outcomes", [])
            for o in outcomes:
                if o.get("description") != qb_name:
                    continue
                name = o.get("name")  # "Over" or "Under"
                point = o.get("point")
                price = o.get("price")
                if point is not None:
                    line_point = float(point)
                if name == "Over":
                    over_price = int(price) if price is not None else None
                elif name == "Under":
                    under_price = int(price) if price is not None else None

        results.append((title, line_point, over_price, under_price))

    return results

def print_qb_ou(team_abbr: str) -> None:
    api_key = get_api_key()

    event = find_next_game(api_key, team_abbr)
    if not event:
        print(f"No upcoming event found in window.")
        return 1

    event_id = event.get("id")
    commence_time = event.get("commence_time")
    home = event.get("home_team")
    away = event.get("away_team")

    bookmakers, headers = fetch_event_player_pass_yds(api_key, event_id)

    # Find the two most common player names in player_pass_yds outcomes
    counts: Dict[str, int] = {}
    for b in bookmakers:
        for m in b.get("markets", []):
            if m.get("key") != "player_pass_yds":
                continue
            for o in m.get("outcomes", []):
                name = o.get("description")
                if not name:
                    continue
                counts[name] = counts.get(name, 0) + 1

    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:2]
    players = [p for p, _ in top]

    result: Dict[str, float] = {}
    for player in players:
        rows = extract_qb_ou(bookmakers, player)
        points = [pt for (_, pt, _, _) in rows if pt is not None]
        if points:
            consensus = sum(points) / len(points)
            result[player] = round(consensus, 1)
    
    remaining = headers.get("x-requests-remaining")
    if remaining is not None:
        print(f"credits_remaining: {remaining}")

def print_all_starting_qb_ou() -> int:
    api_key = get_api_key()

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=12)
    end = now + timedelta(days=8)

    url = f"{ODDS_API_HOST}/v4/sports/{NFL_SPORT_KEY}/events"
    params = {
        "apiKey": api_key,
        "dateFormat": "iso",
        "commenceTimeFrom": _iso(start),
        "commenceTimeTo": _iso(end),
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    events: List[Dict[str, Any]] = resp.json() or []
    events.sort(key=lambda e: e.get("commence_time", ""))

    all_results: Dict[str, float] = {}
    remaining = None
    for e in events:
        event_id = e.get("id")
        bookmakers, headers = fetch_event_player_pass_yds(api_key, event_id)
        if headers is not None:
            remaining = headers.get("x-requests-remaining")

        counts: Dict[str, int] = {}
        for b in bookmakers:
            for m in b.get("markets", []):
                if m.get("key") != "player_pass_yds":
                    continue
                for o in m.get("outcomes", []):
                    name = o.get("description")
                    if not name:
                        continue
                    counts[name] = counts.get(name, 0) + 1

        players = [p for p, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:2]]

        for player in players:
            rows = extract_qb_ou(bookmakers, player)
            points = [pt for (_, pt, _, _) in rows if pt is not None]
            if points:
                consensus = sum(points) / len(points)
                all_results[player] = round(consensus, 1)
    print(json.dumps(all_results))
    for key, value in sorted(all_results.items(), key=lambda item: item[1]):
        print(f"{key}: {value}")
    if remaining is not None:
        print(f"credits_remaining: {remaining}")
    return 0

if __name__ == "__main__":
    print_all_starting_qb_ou()