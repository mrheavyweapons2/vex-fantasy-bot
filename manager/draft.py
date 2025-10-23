"""
File: bot.py
Author: Jeremiah Nairn

Description: Holds all of the functionality for processing the drafts
"""

#neccesary imports
import csv
import os

#main class
class Draft:

    #shared detail variables
    draft_name = None #name of the draft
    people_limit = None #maximum number of people
    pick_limit = None #maximum number of picks
    round_limit = None #number of rounds to be played
    time_limit_min = None #amount of time before the person is skipped
    channel = None #what channel the current draft should be operated in
    announce_channel = None #what channel the announcement was sat in
    announcement_id = None #the message ID for the announcement
    emoji = None #what emoji was used to react to the announcement

    #directory data
    draft_dir = None

    #initilizer
    def __init__(self, name, rounds, limit):
        #get our unique instance values from the initialization
        Draft.draft_name = name
        Draft.round_limit = rounds
        Draft.people_limit = limit
        #create a directory for all of the neccesary files to store data
        Draft.draft_dir = os.path.join("drafts",name)
        os.makedirs(Draft.draft_dir, exist_ok=True)
        print(f"[DRAFT] [FROM {name.upper()}] Directory created at: {Draft.draft_dir}")
        #print to the console
        print(f'[DRAFT] [FROM "{name.upper()}]" Draft Created.')

    #function to log the announcement for the channel
    def log_announcement(self, id, emoji, channel):
        Draft.announcement_id = id
        Draft.emoji = emoji
        Draft.announce_channel = channel

    #function to get the announcement id and emoji from the draft
    def get_announcement_id(self):
        return Draft.announcement_id, Draft.emoji, Draft.announce_channel


    #function that takes a list of tuples containing playerdata, and putting them in a CSV file for setup
    def generate_player_csv(self,playerdata):
        #creates a new csv file in the draft directory
        with open(f"{Draft.draft_dir}/draft_main.csv", mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(("playerid","playername"))
            writer.writerows(playerdata)
    
    def generate_team_csv(self,teams,picks_remaining):
        #creates a new csv file in the draft directory
        with open(f"{Draft.draft_dir}/teams.csv", mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["team", "picks remaining"])
            for team in teams:
                writer.writerow([team, str(picks_remaining)])