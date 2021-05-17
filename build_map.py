#!/usr/bin/env python3
from datetime import datetime
import requests
import folium

from get_access_token import get_access_token

# Slovenia
# SINCE = "2020-06-12"
# UNTIL = "2020-06-22"

# Switzerland 2019
SINCE = "2019-06-29"
UNTIL = "2019-07-14"

# NZ 2017/2018
# SINCE = "2017-12-04"
# UNTIL = "2018-02-15"

# Canary Islands 2021
# SINCE = "2021-02-26"
# UNTIL = "2021-04-19"


def decode_polyline(polyline_str):
    """
    Copied from https://stackoverflow.com/a/33557576
    """
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}

    # Coordinates have variable length when encoded, so just keep
    # track of whether we've hit the end of the string. In each
    # while loop iteration, a single coordinate is decoded.
    while index < len(polyline_str):
        # Gather lat/lon changes, store them in a dictionary to apply them later
        for unit in ['latitude', 'longitude']:
            shift, result = 0, 0

            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break

            if (result & 1):
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = (result >> 1)

        lat += changes['latitude']
        lng += changes['longitude']

        coordinates.append((lat / 100000.0, lng / 100000.0))

    return coordinates


def get_activities(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {"per_page": 20}
    if SINCE:
        data["after"] = datetime.fromisoformat(SINCE).timestamp()
    if UNTIL:
        data["before"] = datetime.fromisoformat(UNTIL).timestamp()
    data["page"] = 1
    while True:
        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers=headers,
            data=data
        )
        activities = response.json()
        if activities:
            data["page"] += 1
            yield from activities
        else:
            break


def main():
    access_token = get_access_token()

    activities = get_activities(access_token)

    the_map = folium.Map(tiles="Stamen Terrain")
    for count, activity in enumerate(activities):
        polyline_str = activity["map"]["summary_polyline"]
        if not polyline_str:
            continue
        points = decode_polyline(activity["map"]["summary_polyline"])
        folium.PolyLine(points, color="red").add_to(the_map)
        popup_text = (
            f"<b>{activity['name']}</b><br>\n"
            f"Distance: {round(activity['distance']/1000, 1)} km<br>\n"
            f"Elevation gain: {activity['total_elevation_gain']} m<br>\n"
            f"<a href='https://www.strava.com/activities/{activity['id']}'>View on Strava</a>"
        )
        popup = folium.map.Popup(html=popup_text)
        folium.Marker(location=points[-1], popup=popup).add_to(the_map)
    boundary = the_map.get_bounds()
    the_map.fit_bounds(boundary, padding=(3, 3))
    the_map.save("map.html")
    print(f"Total activities: {count+1}")
    # print(f"poly: {poly}")
    # print(decode_polyline(poly))


if __name__ == "__main__":
    main()
