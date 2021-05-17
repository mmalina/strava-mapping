# strava-mapping
Create maps from activities on Strava

tl;dr: This project connects to Strava API, fetches activities (based on date interval), builds a map with folium and uploads to a web server

## Motivation

When I go on a long-distance hike that takes several weeks, I want to be able to display a map on my website that shows my progress. All of this needs to
be fully automated. So that when I sync my activity to Garmin Connect
and it gets to Strava, the new activity appears on the progress map
on my website.

## The Workflow

To see the full workflow, check [.github/workflows/build.yaml](.github/workflows/build.yaml)

Here are the main steps:

1. Get access token to Strava API - this is done by `get_access_token.py`
2. Fetch athlete activities via Strava API
3. Create a folium map and add each activity as a polyline
4. Save map to a html file
5. Deploy the html file to a web server

This is the resulting page with the map: http://map.anyberry.net (currently the dates are set to my trip to Switzerland from 2019 for testing)
