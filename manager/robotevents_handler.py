"""
File: bot.py
Author: Jeremiah Nairn

Description: Holds all of the functionality related to the Robotevents API
"""

#base url for the robotevents api
BASE_URL = "https://www.robotevents.com/api/v2"

#imports
import requests

class Robotevent:
    #values to use all over robotevents
    event_sku = None
    api_token = None

    #constructor
    def __init__(self, sku, token):
        #set the variables
        Robotevent.event_sku = sku
        Robotevent.api_token = token

    #gets a list of teams from an event
    def get_teams_from_event():
        url = f"{BASE_URL}/teams?eventCode={Robotevent.event_sku}&per_page=100"
        headers = {
            "Authorization": f"Bearer {Robotevent.api_token}"
        }

        teams = []
        page = 1

        while True:
            response = requests.get(url + f"&page={page}", headers=headers)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch teams: {response.status_code} {response.text}")

            data = response.json()["data"]
            if not data:
                break  # No more teams

            teams.extend(data)
            page += 1

        return teams

