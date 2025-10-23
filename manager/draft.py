"""
File: bot.py
Author: Jeremiah Nairn

Description: Holds all of the functionality for processing the drafts
"""


#main class
class Draft:

    #shared detail variables
    draft_name = None #name of the draft
    people_limit = None #maximum number of people
    round_limit = None #number of rounds to be played
    time_limit_min = None #amount of time before the person is skipped
    channel = None #what channel the current draft should be operated in
    announce_channel = None #what channel the announcement was sat in
    announcement_id = None #the message ID for the announcement
    emoji = None #what emoji was used to react to the announcement

    #directory data
    draft_dir = None

    #draft memory
    teams = []
    draft_data = []

    #initilizer
    def __init__(self, name, rounds, limit):
        #get our unique instance values from the initialization
        self.draft_name = name
        self.round_limit = rounds
        self.people_limit = limit
        #print to the console
        print(f'[DRAFT] [FROM {name.upper()}] Draft Created.')

    #function to log the announcement for the channel
    def log_announcement(self, id, emoji, channel):
        self.announcement_id = id
        self.emoji = emoji
        self.announce_channel = channel

    #function to get the announcement id and emoji from the draft
    def get_announcement_id(self):
        return self.announcement_id, self.emoji, self.announce_channel


    #function that takes a list of dicts containing playerdata
    def generate_player_data(self,player_data):
        pass
    
    #function to generate a list of dicts containing teams and how many picks they have
    def generate_team_data(self,team_data,picks_remaining):
        pass