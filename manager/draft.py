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
    round_limt = None #number of rounds to be played
    time_limit_min = None #amount of time before the person is skipped
    channel = None #what channel the current draft should be operated in


    #initilizer
    def __init__(self, name):
        #get our unique instance values from the initialization
        Draft.draft_name = name
        #print to the console
        print(f'"{name}" created.')
        pass
