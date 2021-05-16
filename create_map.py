#!/usr/bin/env python3
import requests

from get_access_token import get_access_token


def main():
    access_token = get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {"before": 1617256800}
    response = requests.get(
        "https://www.strava.com/api/v3/athletes/7599348/stats",
        headers=headers,
        data=data
    )
    print(f"ytd_ride_totals: {response.json()['ytd_ride_totals']}")


if __name__ == "__main__":
    main()
