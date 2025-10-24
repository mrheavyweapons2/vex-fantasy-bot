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
    total_participants = None

    #directory data
    draft_dir = None

    #draft memory
    teams = []
    draft_data = []
    current_round = 1 #the current round the draft is on
    current_position = 1

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
        print(f'[DRAFT] [FROM {self.draft_name.upper()}] Draft Announced.')

    #function to get the announcement id and emoji from the draft
    def get_announcement_id(self):
        return self.announcement_id, self.emoji, self.announce_channel
    
    #function to return the team data
    def get_teams(self):
        return self.teams
    
    #function to return the queue data
    def get_queue(self, player_id):
        for player_data in self.draft_data:
            if player_data["id"] == player_id:
                picks = [player_data["queue_1"],player_data["queue_2"],player_data["queue_3"],player_data["queue_4"]]
                return picks
            
    #function that takes a list of dicts containing playerdata
    def generate_player_data(self,player_data):
        #for each player, turn them into an expanded dict and add them to the player list
        for current_player in player_data:
            #create the dict
            player = {"id":current_player["id"], "user":current_player["name"],"name":current_player["nick"]} #user data
            #add the extra data
            for r in range(self.round_limit):
                player[f"round_{r+1}"] = None
            #add the rest
            player["double_pick"] = False
            for i in range(4):
                player[f"queue_{i+1}"] = None
            #add the player to the list
            self.draft_data.append(player)
        pass
    
    #function to generate a list of dicts containing teams and how many picks they have
    def generate_team_data(self,team_data,picks_remaining):
        #for each team, turn them into a dict and add them into a new list
        for current_team in team_data:
            #turn into dict and add to list
            team = {"team": current_team, "picks_remaining":picks_remaining}
            self.teams.append(team)
        pass

    #function to make sure the player is a valid participate in the draft
    def validate_participant(self,player_id):
        for player_data in self.draft_data:
            if player_data["id"] == player_id:
                return True
        return False
    
    #function to check if the team is available to pick
    def validate_availability(self,pick):
        #test startments
        success = False
        #make sure the pick is available
        for team in self.teams:
            if team["team"] == pick:
                #team found
                success = True
                if team["picks_remaining"] == 0:
                    success = False
        return success
    
    #function to clear the users picks
    def clear_picks(self,player_id):
        player_data = next((pd for pd in self.draft_data if pd.get("id") == player_id), None)
        if player_data is None:
            return False
        #set all of the queue picks to none
        for queue in range (4):
            player_data[f"queue_{queue+1}"] = None
        player_data["double_pick"] = False
        return True

    #function to pick for a player from the queue (needs to be rewritten)
    def pick_one(self,player_id,pick):
        #check if you can pick them
        success = False
        if self.clear_picks(player_id):
            if self.validate_availability(pick):
                success = True
                #set players pick in the queue
                for player_data in self.draft_data:
                    if player_data["id"] == player_id:
                        player_data["queue_1"] = pick
                        player_data["double_pick"] = False
                        #print check to console
                        print(f'[DRAFT] [FROM {self.draft_name.upper()}] {player_data["name"]} has picked {pick}')
                    else:
                        success = False
        #return false if found is false, otherwise true
        return success

    #function to add more teams to a players queue
    def pick_multiple(self, player_id, picks, doublepick):
        success = False
        #clear the picks
        if self.clear_picks(player_id):
            #find the player once
            player_data = next((pd for pd in self.draft_data if pd.get("id") == player_id), None)
            if player_data is None:
                return False
            #iterate over picks without mutating the input and fill up to 4 slots
            assigned = 0
            for pick in picks:
                if assigned >= 4:
                    break
                if not self.validate_availability(pick):
                    continue
                #set player's queue slot (1-based) and double_pick flag
                player_data[f"queue_{assigned+1}"] = pick
                player_data["double_pick"] = doublepick
                #log and mark success
                print(f'[DRAFT] [FROM {self.draft_name.upper()}] {player_data["name"]} has picked {pick}')
                success = True
                assigned += 1
        return success
