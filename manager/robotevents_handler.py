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
    #api token
    api_token = None
    #values to use all over robotevents
    event_name = None
    event_sku = None
    event_id = None

    #constructor
    def __init__(self, name, sku, token):
        #set the variables
        self.event_sku = sku
        self.api_token = token
        self.event_name = name
        #get th events id
        self.get_event_id()

    #access the event through the API

    def get_event_id(self):
        if self.event_id == None:
            #json request parameters
            url = "https://www.robotevents.com/api/v2/events"
            params = {"sku": {self.event_sku}}
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json"
                }
            #get a response from the api, and get the event id from the event sku
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            #pull the event id
            self.event_id = data["data"][0]["id"]
            print(f"[ROBOTEVENTS] [FROM {(self.event_name).upper()}] Event ID Acquired: {self.event_id}")
        else:
            return self.event_id

    def get_teams_from_event(self):
        #get the list of teams
        teams = []
        #json request parameters
        url = f"{BASE_URL}/events/{self.event_id}/teams"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json"
            }
        #request the data
        response = requests.get(url, headers=headers)
        data = response.json()
        #extract team numbers
        teams = [team["number"] for team in data.get("data", [])]
        print(f"[ROBOTEVENTS] [FROM {(self.event_name).upper()}] Teams Acquired from {self.event_id}")
        #return the teams
        return teams

