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
from math import sin, cos, sqrt, atan2, radians

from get_access_token import get_access_token

ACTIVITIES_ENDPOINT = "https://www.strava.com/api/v3/athlete/activities"

# France 2022
SINCE = "2022-07-01"
UNTIL = "2022-07-11"

# Scotland 2022
# SINCE = "2022-04-14"
# UNTIL = "2022-04-24"

# Nepal 2021
# SINCE = "2021-11-21"
# UNTIL = "2021-12-04"

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
# SINCE = "2021-07-16"
# UNTIL = "2021-08-08"

# Fuerteventura Fall 2021
# SINCE = "2021-10-25"
# UNTIL = "2021-11-06"


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
    payload = {"per_page": 20}
    if SINCE:
        payload["after"] = datetime.fromisoformat(SINCE).timestamp()
    if UNTIL:
        payload["before"] = datetime.fromisoformat(UNTIL).timestamp()
    payload["page"] = 1
    while True:
        response = requests.get(
            ACTIVITIES_ENDPOINT,
            headers=headers,
            params=payload,
        )
        if response.status_code != requests.codes.ok:
            print("Failed to get activities")
            print(f"Request url: {ACTIVITIES_ENDPOINT}")
            print(f"Request headers: {headers}")
            print(f"Request payload: {payload}")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            break
        activities = response.json()
        if activities:
            payload["page"] += 1
            yield from activities
        else:
            break


def get_activity_photos(access_token, activity_id, size=None):
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"photo_sources": True}
    if size is not None:
        payload["size"] = size
    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}/photos",
        headers=headers,
        params=payload,
    )
    if response.status_code != requests.codes.ok:
        print("Failed to get photos, skipping...")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return []
    return response.json()


def get_distance(loc1, loc2):
    """Simple implentation of Haversine algorithm. It assumes earth is a sphere,
    so not very accurate, but good enough for this use case and no need
    to import another library (geopy.distance)

    Returns: distance between two coordinates in km
    """
    # approximate radius of earth in km
    R = 6373.0

    lat1 = radians(loc1[0])
    lon1 = radians(loc1[1])
    lat2 = radians(loc2[0])
    lon2 = radians(loc2[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c

    return distance


def main():
    access_token = get_access_token()

    # Unfortunately Strava API does not allow to specify
    # activities order - it's always newest to oldest.
    # And we need oldest to newest because of avoiding
    # markers near each other - the older activity
    # will create the marker as usual and the newer activity
    # will use the mid-point instead.
    # But it's a pitty we can't use the generator properly :(
    activities = reversed(list(get_activities(access_token)))

    the_map = folium.Map(tiles=None, control_scale=True)
    folium.TileLayer("Stamen Terrain", detect_retina=True).add_to(the_map)
    folium.TileLayer("OpenStreetMap", detect_retina=True).add_to(the_map)
    fg = folium.FeatureGroup(name="Show Photos", show=False)
    the_map.add_child(fg)
    folium.LayerControl(collapsed=False).add_to(the_map)
    Fullscreen().add_to(the_map)

    count = 0
    marker_locations = []
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
        marker_loc = points[-1]
        # Avoid markers that are close to each other. If the end point
        # of the activity is close to any previous marker, use the mid-point
        # of the activity instead.
        if any([get_distance(loc, marker_loc) < 1 for loc in marker_locations]):
            marker_loc = points[len(points)//2]
        folium.Marker(location=marker_loc, popup=popup).add_to(the_map)
        marker_locations.append(marker_loc)
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
