#!/usr/bin/env python3
"""Build folium map from Strava activities using Strava API

User activities are loaded from newest to oldest. They are paged by 20 items.
For each activity there are extra 2 api requests to get photos. The api rate limit
is 100 requests per 15 minutes. This means 48 is the maximum amount of activities
that can be loaded at once.

The date boundaries for activities are set via SINCE/UNTIL constants
here at the top of the script.
"""
from datetime import datetime
import requests
import folium
from folium.plugins import Fullscreen

from get_access_token import get_access_token

# Slovenia
# SINCE = "2020-06-12"
# UNTIL = "2020-06-22"

# Switzerland 2019
# SINCE = "2019-06-29"
# UNTIL = "2019-07-14"
# UNTIL = "2019-07-05"

# NZ 2017/2018
# SINCE = "2017-12-04"
# UNTIL = "2018-02-15"

# Canary Islands 2021
# SINCE = "2021-02-26"
# SINCE = "2021-04-09"
# UNTIL = "2021-04-19"

# Switzerland 2021
# SINCE = "2021-06-27"
SINCE = "2021-07-16"
UNTIL = "2021-08-08"


def decode_polyline(polyline_str):
    """
    Copied from https://stackoverflow.com/a/33557576
    """
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {"latitude": 0, "longitude": 0}

    # Coordinates have variable length when encoded, so just keep
    # track of whether we've hit the end of the string. In each
    # while loop iteration, a single coordinate is decoded.
    while index < len(polyline_str):
        # Gather lat/lon changes, store them in a dictionary to apply them later
        for unit in ["latitude", "longitude"]:
            shift, result = 0, 0

            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if not byte >= 0x20:
                    break

            if result & 1:
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = result >> 1

        lat += changes["latitude"]
        lng += changes["longitude"]

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
            data=data,
        )
        if response.status_code != requests.codes.ok:
            print("Failed to get activities")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            break
        activities = response.json()
        if activities:
            data["page"] += 1
            yield from activities
        else:
            break


def get_activity_photos(access_token, activity_id, size=None):
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {"photo_sources": True}
    if size is not None:
        data["size"] = size
    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}/photos",
        headers=headers,
        data=data,
    )
    if response.status_code != requests.codes.ok:
        print("Failed to get photos, skipping...")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return []
    return response.json()


def main():
    access_token = get_access_token()

    activities = get_activities(access_token)

    the_map = folium.Map(tiles=None, control_scale=True)
    folium.TileLayer("Stamen Terrain", detect_retina=True).add_to(the_map)
    folium.TileLayer("OpenStreetMap", detect_retina=True).add_to(the_map)
    fg = folium.FeatureGroup(name="Show Photos", show=False)
    the_map.add_child(fg)
    folium.LayerControl(collapsed=False).add_to(the_map)
    Fullscreen().add_to(the_map)
    # Railway station in St. Moritz
    folium.Marker(
        location=(46.49811030370744, 9.846421184253723),
        icon=folium.Icon(icon="train", prefix="fa"),
        popup="St. Moritz Railway Station",
    ).add_to(the_map)
    count = 0
    for activity in activities:
        polyline_str = activity["map"]["summary_polyline"]

        if not polyline_str:
            continue
        points = decode_polyline(activity["map"]["summary_polyline"])
        folium.PolyLine(points, color="red").add_to(the_map)
        popup_text = (
            f"<div style='width: 15em'><b>{activity['name']}</b><br><br>\n"
            f"Distance: {round(activity['distance']/1000, 1)} km<br>\n"
            f"Elevation gain: {round(activity['total_elevation_gain'])} m<br><br>\n"
            f"<a href='https://www.strava.com/activities/{activity['id']}'>"
            "View on Strava</a></div>"
        )
        popup = folium.map.Popup(html=popup_text)
        # folium.Marker(location=points[len(points)//2], popup=popup).add_to(the_map)
        folium.Marker(location=points[-1], popup=popup).add_to(the_map)
        size = "400"
        photos_thumb = get_activity_photos(access_token, activity["id"])
        photos_large = get_activity_photos(access_token, activity["id"], size=size)
        # If we fail to get either thumbs or large photos, just skip the photos
        for photo in range(min(len(photos_thumb), len(photos_large))):
            if "location" not in photos_thumb[photo]:
                continue
            icon = folium.CustomIcon(
                photos_thumb[photo]["urls"]["0"],
                icon_size=photos_thumb[photo]["sizes"]["0"],
            )
            popup = folium.map.Popup(
                html=f"<img src='{photos_large[photo]['urls'][size]}'>"
            )
            folium.Marker(
                location=photos_thumb[photo]["location"], icon=icon, popup=popup
            ).add_to(the_map).add_to(fg)
        count += 1

    boundary = the_map.get_bounds()
    the_map.fit_bounds(boundary, padding=(3, 3), max_zoom=13)
    the_map.save("map.html")
    print(f"Total activities: {count}")


if __name__ == "__main__":
    main()
