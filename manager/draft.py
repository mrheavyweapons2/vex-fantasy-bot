"""
File: bot.py
Author: Jeremiah Nairn

Description: Holds all of the functionality for processing the drafts
"""

import csv

#main class
class Draft:

    #shared detail variables
    draft_name = None #name of the draft
    people_limit = None #maximum number of people
    pick_limit = None #maximum number of picks
    round_limit = None #number of rounds to be played
    time_limit_min = None #amount of time before the person is skipped
    channel = None #what channel the current draft should be operated in

    #directory data
    


    #initilizer
    def __init__(self, name, rounds, limit):
        #get our unique instance values from the initialization
        Draft.draft_name = name
        Draft.round_limit = rounds
        Draft.people_limit = limit
        #create a directory for all of the neccesary files to store data

        #print to the console
        print(f'"{name}" draft created.')
        pass
