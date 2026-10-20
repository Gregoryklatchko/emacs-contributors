import os
import requests
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

REPO = "emacs-mirror/emacs"
API = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github+json"}
if os.getenv("GITHUB_TOKEN"):
    HEADERS["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"

def get(url, **kwargs):
    response = requests.get(url, headers=HEADERS, timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()

# GitHub's repository contributors endpoint sorts by contribution count.
contributors = get(
    f"{API}/repos/{REPO}/contributors",
    params={"per_page": 100},
)

geolocator = Nominatim(user_agent="emacs-contributor-country-analysis")
geocode = RateLimiter(
    geolocator.geocode,
    min_delay_seconds=1.1,
    swallow_exceptions=True,
)

rows = []
for rank, contributor in enumerate(contributors, start=1):
    profile = get(contributor["url"])
    location = (profile.get("location") or "").strip()
    country = "Unknown" if not location else "Unresolved"

    if location:
        result = geocode(location, addressdetails=True)
        if result:
            country = result.raw.get("address", {}).get("country", "Unresolved")

    rows.append({
        "rank": rank,
        "username": contributor["login"],
        "contributions": contributor["contributions"],
        "profile_location": location,
        "country": country,
        "profile_url": profile["html_url"],
    })
    print(f"{rank}/{len(contributors)}: {contributor['login']} — {country}")

df = pd.DataFrame(rows)
df.to_csv("contributors.csv", index=False)

summary = (
    df.groupby("country")
      .size()
      .reset_index(name="contributors")
      .sort_values("contributors", ascending=False)
)
summary.to_csv("country_summary.csv", index=False)

print("\nCountry summary:")
print(summary.to_string(index=False))
print("\nCreated contributors.csv and country_summary.csv")
