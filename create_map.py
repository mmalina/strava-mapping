#!/usr/bin/env python3
"""

Login cookie is saved to COOKIES_FILE so that subsequent runs of the script
don't need to login again.

Required env vars (either already set, or present in .env):
STRAVA_EMAIL
STRAVA_PASSWORD
"""
import os
import sys
import logging
import urllib.parse
import requests

import mechanize
from dotenv import load_dotenv


COOKIES_FILE = "cookies.txt"
logger = logging.getLogger("mechanize.http_redirects")
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)


def load_cookiejar():
    cj = mechanize.LWPCookieJar(COOKIES_FILE)
    if os.path.exists(COOKIES_FILE):
        logger.info(f"Loading cookie from {COOKIES_FILE}")
        cj.load(COOKIES_FILE, ignore_discard=True, ignore_expires=True)
    return cj


def login(br, cj):
    br.open('https://strava.com/login')
    br.select_form(nr=0)    # selects the first form on the login page
    br.form['email'] = os.environ["STRAVA_EMAIL"]
    br.form['password'] = os.environ["STRAVA_PASSWORD"]
    br.submit()
    cj.save(COOKIES_FILE, ignore_discard=True, ignore_expires=True)


def get_api_token():
    return


def main():
    load_dotenv()  # Load env vars from .env for development

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

    print(response.status_code)
    print(response.headers["Location"])

    api_token = get_api_token()


if __name__ == "__main__":
    main()
