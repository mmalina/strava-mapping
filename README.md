# strava-mapping
Create maps from activities on Strava

tl;dr: This project connects to Strava API, fetches activities (based on date interval), builds a map with folium and uploads to a web server

## Motivation

When I go on a long-distance hike that takes several weeks, I want to be able to display a map on my website that shows my progress. All of this needs to
be fully automated. So that when I sync my activity to Garmin Connect
and it gets to Strava, the new activity appears on the progress map
on my website.

## The Workflow

To see the full workflow, check [.github/workflows/build.yaml](.github/workflows/build.yaml). The workflow is triggered manually. There is an API for that and I have a shortcut set up in iOS Shortcuts app, so it's a matter of one click for me. It would be nice to be able to use Strava webhooks to trigger a new workflow run automatically for new activities. But for that I would need to create a service that would glue together Strava subscriptions and Github webhooks.

Here are the main steps:

1. Get access token to Strava API - this is done by `get_access_token.py`
2. Fetch athlete activities via Strava API
3. Create a folium map and add each activity as a polyline
4. Save map to a html file
5. Deploy the html file to a web server

This is the resulting page with the map: http://map.anyberry.net (currently the dates are set to my latest trip to the Alps)

## Strava API access caveats

First thing that is required is an app created in Strava. This can easily be done at https://www.strava.com/settings/api .
But then the user needs to authorize the app to access his or her data. This is done via a form on a webpage (via oath).
Once the logged in user confirms the form, they would be redirected to a page the app provides. The request contains
a code that can be exchanged for a short-lived access_token and a refresh_token. The access_token is only valid for
6 hours after which you need to obtain a new one using the refresh_token (which will also give you a new refresh_token).
If I wanted to authorize once and then only use the tokens, I would need to persist the token somewhere (Github
doesn't provide any sort of secret store to save data to). So I needed to automate the app authorization step.
Once I had that, I was able to obtain the access_token and call Strava API as needed.
