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
    channel = None #what channel the current draft should be operated in
    announce_channel = None #what channel the announcement was sat in
    announcement_id = None #the message ID for the announcement
    emoji = None #what emoji was used to react to the announcement
    bot = None
    total_participants = 0 #the total number of participants in the draft

    #directory data
    draft_dir = None

    #draft memory
    teams = []
    draft_data = []
    current_round = 0 #the current round the draft is on
    current_position = 1 #the current position the draft is on
    time_limit_min = None #amount of time (in minutes) before the person is skipped automatically
    skip_check = False #will skip the current persons turn if set to true

    #initilizer
    def __init__(self, name, rounds, limit, bot):
        #get our unique instance values from the initialization
        self.draft_name = name
        self.round_limit = rounds
        self.people_limit = limit
        self.bot = bot
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
            #add the queue spots
            for i in range(4):
                player[f"queue_{i+1}"] = None
            #give the player a position
            player["position"] = 0
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
                        success = True
                        break
                    else:
                        success = False
        #return false if found is false, otherwise true
        return success

    #function to add more teams to a players queue
    def pick_multiple(self, player_id, picks):
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
                #log and mark success
                print(f'[DRAFT] [FROM {self.draft_name.upper()}] {player_data["name"]} has picked {pick}')
                success = True
                assigned += 1
        return success

    #function to put a pick in queue and validate if it processed
    def process_pick(self, position):
        # find player by draft position
        player_data = next((pd for pd in self.draft_data if pd.get("position") == position), None)
        if player_data is None:
            return False
        
        self.current_round + 1
        round_field = f"round_{self.current_round}"

        # loop until we consume a valid pick or there are no picks left
        while True:
            pick = player_data.get("queue_1")
            if pick is None:
                return False

            # if round field is invalid, drop this pick and shift left
            if round_field not in player_data:
                player_data["queue_1"] = player_data.get("queue_2")
                player_data["queue_2"] = player_data.get("queue_3")
                player_data["queue_3"] = player_data.get("queue_4")
                player_data["queue_4"] = None
                continue

            # ensure the pick is still available (team exists and has picks)
            team_entry = next((t for t in self.teams if t["team"] == pick), None)
            if team_entry is None or team_entry.get("picks_remaining", 0) <= 0:
                # drop the invalid pick and shift left
                player_data["queue_1"] = player_data.get("queue_2")
                player_data["queue_2"] = player_data.get("queue_3")
                player_data["queue_3"] = player_data.get("queue_4")
                player_data["queue_4"] = None
                continue

            # place the pick into the current round
            player_data[round_field] = pick
            team_entry["picks_remaining"] -= 1

            # shift the queue forward (queue_2 -> queue_1, etc.)
            player_data["queue_1"] = player_data.get("queue_2")
            player_data["queue_2"] = player_data.get("queue_3")
            player_data["queue_3"] = player_data.get("queue_4")
            player_data["queue_4"] = None

            # reset double_pick flag since a pick was consumed
            player_data["double_pick"] = False

            print(f'[DRAFT] [FROM {self.draft_name.upper()}] {player_data["name"]} picked {pick} for Round {self.current_round}')
            return True
        
    #function return a players picks
    def get_picks(self,player_id):
        #find the players entry in the list
        for player_data in self.draft_data:
            if player_data["id"] == player_id:
                #make an empty list, and add all of the picks to it
                picks = []
                for r in range(self.round_limit):
                    picks.append(player_data[f"round_{r+1}"])
                return picks