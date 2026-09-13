from __future__ import annotations


"""Live data fetchers. Raw payloads only; parsing lives in compute. Any failure dies without writing."""


import requests

from kit import die


API_URL = "https://api.github.com/graphql"


QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
    repositories(first: 50, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        name
        description
        primaryLanguage { name color }
        stargazerCount
        pushedAt
        visibility
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch_live(user: str, token: str) -> dict:
    """Single GraphQL fetch; dies (writing nothing) on any failure."""
    try:
        response = requests.post(
            API_URL,
            json={"query": QUERY, "variables": {"login": user}},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
    except requests.RequestException as exc:
        die(f"GitHub API request failed: {exc}")
    if response.status_code != 200:
        die(f"GitHub API HTTP {response.status_code}: {response.text[:200]}")
    try:
        payload = response.json()
    except ValueError:
        die("GitHub API returned non-JSON response")
    if payload.get("errors"):
        die(f"GitHub API GraphQL errors: {json.dumps(payload['errors'])[:300]}")
    data = payload.get("data", {}).get("user")
    if not data:
        die(f"user {user!r} not found in API response")
    return data


def fetch_public(user: str) -> dict:
    """No-token REAL-data tier: public endpoints only (never fabricates).

    Contributions come from the public contributions calendar mirror
    (github-contributions-api.jogruber.de/v4); repos from the REST API.
    Language byte-breakdowns only for the 5 most recent public repos
    (unauthenticated rate limits). Any failure dies without writing."""
    try:
        r = requests.get(
            f"https://github-contributions-api.jogruber.de/v4/{user}?y=last",
            timeout=30,
        )
        if r.status_code != 200:
            die(f"public contributions HTTP {r.status_code}")
        days = (r.json().get("contributions") or [])
        if not days:
            die("public contributions returned no data")
    except requests.RequestException as exc:
        die(f"public contributions request failed: {exc}")
    dated = sorted((str(d["date"]), int(d["count"])) for d in days)[-364:]
    while len(dated) % 7:
        dated.insert(0, dated[0])
    total = sum(count for _date, count in dated)
    try:
        r = requests.get(
            f"https://api.github.com/users/{user}/repos?per_page=50&sort=pushed",
            timeout=30,
        )
        if r.status_code != 200:
            die(f"REST repos HTTP {r.status_code}")
        nodes = r.json()
    except requests.RequestException as exc:
        die(f"REST repos request failed: {exc}")
    repo_nodes = []
    lang_calls = 0
    for node in nodes:
        if node.get("fork") or node.get("private") or node.get("name") == user:
            continue
        edges = []
        if lang_calls < 5:
            lang_calls += 1
            try:
                lr = requests.get(
                    f"https://api.github.com/repos/{user}/{node['name']}/languages",
                    timeout=30,
                )
                if lr.status_code == 200:
                    edges = [
                        {"node": {"name": name, "color": None}, "size": int(size)}
                        for name, size in sorted(lr.json().items(), key=lambda kv: -kv[1])[:8]
                    ]
            except requests.RequestException:
                pass
        repo_nodes.append(
            {
                "name": node["name"],
                "description": node.get("description") or "",
                "primaryLanguage": ({"name": node["language"]} if node.get("language") else None),
                "stargazerCount": int(node.get("stargazers_count") or 0),
                "pushedAt": node.get("pushed_at") or "",
                "visibility": "PUBLIC",
                "languages": {"edges": edges},
            }
        )
    return {
        "contributionsCollection": {
            "contributionCalendar": {
                "totalContributions": total,
                "weeks": [
                    {
                        "contributionDays": [
                            {"contributionCount": count, "date": date}
                            for date, count in dated[i : i + 7]
                        ]
                    }
                    for i in range(0, len(dated), 7)
                ],
            }
        },
        "repositories": {"nodes": repo_nodes},
    }


def fetch_weather() -> tuple[int, int] | None:
    """(temperature C, WMO weather code) for Delhi right now, or None."""
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": 28.61, "longitude": 77.21,
                    "current": "temperature_2m,weather_code"},
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f"weather: request failed ({exc}); scene renders without it")
        return None
    if response.status_code != 200:
        print(f"weather: HTTP {response.status_code}; scene renders without it")
        return None
    try:
        current = response.json()["current"]
        return int(current["temperature_2m"]), int(current["weather_code"])
    except (ValueError, KeyError, TypeError) as exc:
        print(f"weather: bad payload ({exc}); scene renders without it")
        return None
