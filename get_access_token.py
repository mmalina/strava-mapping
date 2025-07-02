#!/usr/bin/env python3
"""
Get access_token for Strava API access

This assumes you have an app created at https://www.strava.com/settings/api

The script will login to Strava as a normal user, then authorize the app
to access use data (scope activities:read) and get an access token (valid
for 6 hours).

The script automatically reuses existing data if present:
1. Login cookie is saved to COOKIES_FILE so that subsequent runs of the script
   don't need to login again.
2. refresh_token is saved to TOKEN_JSON so that on subsequent runs we try
   to use that to get a new token directly and if it works, Strava
   login and authorization are skipped

Required env vars (either already set, or via .env file):
STRAVA_EMAIL
STRAVA_PASSWORD
STRAVA_API_CLIENT_ID
STRAVA_API_CLIENT_SECRET
"""
import os
import urllib.parse
import requests
import json

import mechanize
from dotenv import load_dotenv


COOKIES_FILE = "cookies.txt"
TOKEN_JSON = "token.json"
STRAVA_API_URL = "https://www.strava.com/api/v3"


def load_and_refresh_token():
    """Load token from TOKEN_JSON and refresh it

    Returns access_token if we could successfully load refresh_token
    and get a new token. Otherwise return None.
    """
    if os.path.isfile(TOKEN_JSON):
        print(f"Loading tokens from {TOKEN_JSON}")
        with open(TOKEN_JSON, "r") as f:
            token = json.load(f)
        data = {
            "client_id": os.environ["STRAVA_API_CLIENT_ID"],
            "client_secret": os.environ["STRAVA_API_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"]
        }
        print("Refreshing token")
        response = requests.post("https://www.strava.com/oauth/token", data=data)
        if not response.ok:
            print(f"Could not refresh token: {response.status_code} {response.reason}")
            return None
        values = response.json()
        with open(TOKEN_JSON, "w") as f:
            json.dump(values, f)
        print("Successfully loaded and refreshed token")
        return values["access_token"]
    # STRAVA_REFRESH_TOKEN set in env
    elif "STRAVA_REFRESH_TOKEN" in os.environ:
        print("Using STRAVA_REFRESH_TOKEN from env")
        data = {
            "client_id": os.environ["STRAVA_API_CLIENT_ID"],
            "client_secret": os.environ["STRAVA_API_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"]
        }
        response = requests.post("https://www.strava.com/oauth/token", data=data)
        if not response.ok:
            print(f"Could not refresh token: {response.status_code} {response.reason}")
            return None
        values = response.json()
        with open(TOKEN_JSON, "w") as f:
            json.dump(values, f)
        print("Successfully loaded and refreshed token from env")
        return values["access_token"]
    return None


def authorize_and_get_token():
    br = mechanize.Browser()
    cj = load_cookiejar()
    br.set_cookiejar(cj)
    br.set_handle_robots(False)
    br.open('https://strava.com/dashboard')
    if "login" in br.geturl():  # We got redirected to login
        print("Login required. Logging in...")
        login(br, cj)

    get_params = {
        "response_type": "code",
        "client_id": os.environ["STRAVA_API_CLIENT_ID"],
        "redirect_uri": "http://localhost/oauth-redirect",
        "scope": "activity:read"
    }
    br.open("https://www.strava.com/api/v3/oauth/authorize?"
            + urllib.parse.urlencode(get_params))
    br.select_form(nr=0)
    # Simply using br.submit() would be best, but it follows the redirect
    # which is not desired. This is a workaround for that.
    request = br.click()
    response = requests.post(
        request.full_url,
        data=request.data,
        cookies=cj,
        allow_redirects=False
    )

    loc = response.headers["Location"]
    query = urllib.parse.urlparse(loc).query
    params = urllib.parse.parse_qs(query)
    code = params["code"][0]
    data = {
        "client_id": os.environ["STRAVA_API_CLIENT_ID"],
        "client_secret": os.environ["STRAVA_API_CLIENT_SECRET"],
        "code": code,
        "grant_type": "authorization_code"
    }
    response = requests.post("https://www.strava.com/oauth/token", data=data)
    values = response.json()
    with open(TOKEN_JSON, "w") as f:
        json.dump(values, f)
    print("Successfully got token")
    return values["access_token"]


def load_cookiejar():
    cj = mechanize.LWPCookieJar(COOKIES_FILE)
    if os.path.exists(COOKIES_FILE):
        print(f"Loading cookie from {COOKIES_FILE}")
        cj.load(COOKIES_FILE, ignore_discard=True, ignore_expires=True)
    return cj


def login(br, cj):
    br.open('https://strava.com/login')
    br.select_form(nr=0)    # selects the first form on the login page
    br.form['email'] = os.environ["STRAVA_EMAIL"]
    br.form['password'] = os.environ["STRAVA_PASSWORD"]
    br.submit()
    cj.save(COOKIES_FILE, ignore_discard=True, ignore_expires=True)


def get_access_token():
    load_dotenv()  # Load env vars from .env for development

    # First try to get the token from $TOKEN_JSON
    access_token = load_and_refresh_token()
    # If that didn't work, login to Strava, authorize the app and get new token
    if access_token is None:
        access_token = authorize_and_get_token()

    return access_token


def main():
    access_token = get_access_token()
    print(f"Access token: {access_token}")


if __name__ == "__main__":
    main()
