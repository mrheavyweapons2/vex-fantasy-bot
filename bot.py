"""
File: bot.py
Author: Jeremiah Nairn

Description: This is a fantasy draft bot built specificly for vex and robotevents.
"""

'''
update roadmap:

-allow a way for people to pick for themselves after the draft bot has skipped them

-begin to allow the bot to tell time
    -allow draft admins to set a minimum time limit
    -have the bot automatically skip turns or random pick if the time limit is exceeded
    -implement a downtime where the bot will not skip turns

-allow the draft bot to handle simultaneous picking in the draft order
    -(meaning if person 1 is taking forever, person 2 can pick while waiting, if there is 2 or more remaining picks for a team)

-rewrite some code to be more efficient and cleaner if need be

-fix any bugs that arise from testing and usage post release 2.0
    
-begin drafting the scoring system into the bot (will come after release 2.0)
'''

#import draft
from manager import draft
#import excel
from manager import excel

#imports discord token from an encrypted .env file
import os
from dotenv import load_dotenv

#load variables from .env file
load_dotenv()  
DS_TOKEN = os.getenv("DISCORD_TOKEN")
RB_TOKEN = os.getenv("ROBOTEVENTS_TOKEN")

#get the admin bypass ids
ADMIN_BYPASS_IDS = os.getenv("ADMIN_BYPASS_IDS").split(",")
for i in range(len(ADMIN_BYPASS_IDS)):
    ADMIN_BYPASS_IDS[i] = int(ADMIN_BYPASS_IDS[i])

#discord imports
import discord
from discord import app_commands
from discord.ext import commands

#import other neccessary modules
import time
import threading
import asyncio
import csv
import tempfile

#setup intents (just message_content isn't needed for slash commands, but safe to keep)
intents = discord.Intents.default()
intents.reactions = True
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

#assigns "!" as the command prefix for all commands
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

"""
DISCORD PAGINATION
    -class: Pagination (handles all of the pagination for long messages or guides)
    -function: get_available_picks (shows the user all of the available picks and utilizes pagination)
"""

class Paginator(discord.ui.View):
    #constructor
    def __init__(self, items, per_page=5, embed_fn=None, timeout=180):
        #declares variables and calls super
        super().__init__(timeout=timeout)
        self.items = items
        self.per_page = per_page
        self.page = 0
        self.embed_fn = embed_fn or self.default_embed

    def default_embed(self, items, page, total_pages):
        """Default embed generator if none provided"""
        embed = discord.Embed(
            title=f"Page {page + 1}/{total_pages}",
            description="\n".join(items),
            color=discord.Color.blurple()
        )
        return embed

    #gets the items for the current page
    def get_page_items(self):
        start = self.page * self.per_page
        end = start + self.per_page
        return self.items[start:end]

    #updates the message with the new page
    async def update_message(self, interaction):
        total_pages = (len(self.items) - 1) // self.per_page + 1
        embed = self.embed_fn(self.get_page_items(), self.page, total_pages)
        await interaction.response.edit_message(embed=embed, view=self)

    #button to go to the previous page
    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()

    #button to go to the next page
    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_pages = (len(self.items) - 1) // self.per_page + 1
        if self.page < total_pages - 1:
            self.page += 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()

"""
HELPER FUNCTIONS
    -is_admin (checks of the user is an admin)
    -validation_check(checks if the user is in the draft and in the correct channel)
    -run_draft (runs the main draft for picking teams)
"""

#function to return true if the user is an administator, false if not
def is_admin(interaction: discord.Interaction) -> bool:
    '''
    helper function that validates if the user is an administrator or a bypassed ID

    :param interaction: the raw discord interaction object to check the user
    :type interaction: discord.Interaction
    :return: True if the user is an admin or bypassed, False otherwise
    :rtype: bool
    '''
    try:
        user = interaction.user
        # explicit bypass
        if getattr(user, "id", None) in ADMIN_BYPASS_IDS:
            return True
        #guild permissions (only present when running in a guild context)
        perms = getattr(user, "guild_permissions", None)
        if perms and getattr(perms, "administrator", False):
            return True
    except Exception:
        #any unexpected error -> deny by default
        return False
    return False

#function to validate if the user is allowed to run the 
def validation_check(interaction: discord.Interaction) -> bool:
    '''
    helper function that connects the drafter ID and channel to a draft instance

    :param interaction: the raw discord interaction object to check for an id and channel
    :type interaction: discord.Interaction
    :return: True if the user is communicating in the correct draft channel and is an active participant, false Otherwise
    :rtype: bool
    '''
    for draft in drafts:
        if drafts[draft].channel == interaction.channel:
            #validate and make sure person is in the draft
            if drafts[draft].validate_participant(interaction.user.id) == True:
                #code here
                return True, draft
    return False, None

#function to run the draft
def run_draft(draft_instance,bot):
    '''
    function that runs the main draft for picking teams

    :param draft_instance: the class object that houses all of the data for the draft
    :type draft_instance: Class Object
    :param bot: the bot object
    :type bot: idk
    '''
    #get the draft data
    drafters = draft_instance.draft_data
    #helper function to get the snake position in the draft and the round
    def get_snake_position(real_position):
        """
        returns the round number and draft position for a given real position
        in a snake-style draft.

        :param real_position: the absolute pick number (starting at 0)
        :type real_position: int
        :return: (round_number, position_in_round)
        """
        #get the round number
        round_number = (real_position // draft_instance.total_participants)
        #gets the position in the round
        index_in_round = real_position % draft_instance.total_participants
        if round_number % 2 == 0:
            position_in_round = index_in_round
        else:
            position_in_round = draft_instance.total_participants - 1 - index_in_round
        #return both values
        return round_number+1, position_in_round
    #go through each round (real position is where the draft currently is based on total participants and rounds, and not on snake position)
    for real_position in range(draft_instance.total_participants*draft_instance.round_limit):
        #use the helper function to get the current round and snake position for the main player
        round, draft_instance.current_position = get_snake_position(real_position)
        for drafter in drafters:
            #identify the drafter who is in this position
            if drafter["position"] == draft_instance.current_position:
                #debouncer
                debounce = True
                warningDebounce = True
                #check and see if their queue can be processed
                while not draft_instance.process_pick(draft_instance.current_position,round):
                    #check if skip has been requested
                    if draft_instance.skip_check:
                        draft_instance.skip_check = False
                        print(f"[BOT] [FROM {draft_instance.draft_name}] Turn Skipped.")
                        break
                    #check and see if the time limit has been exceeded
                    if draft_instance.time_limit_min > 0:
                        current_time = time.time()
                        elapsed_time = (current_time - draft_instance.time_memory) / 60  # convert to minutes
                        if elapsed_time >= draft_instance.time_limit_min:
                            #warn the user if they pass the warning time in minutes
                            if warningDebounce and draft_instance.should_warn():
                                warningDebounce = False
                                if getattr(draft_instance, "channel", None) is not None:
                                    asyncio.run_coroutine_threadsafe(
                                        draft_instance.channel.send(f"<@{now_up}> has {draft_instance.timer_warning} minutes before they are skipped."),
                                        draft_instance.bot.loop
                                    )
                            if draft_instance.is_in_downtime():
                                #in downtime, do not skip
                                continue
                            print(f"[BOT] [FROM {draft_instance.draft_name}] Time Limit Exceeded. Skipping Turn.")
                            #random pick for the drafter
                            draft_instance.pick_random(drafter["id"])
                            break
                    #ping who is up, who is on deck, and who is in the2 hole (only once per turn)
                    if debounce:
                        debounce = False  
                        #get the ids of the three players
                        now_up = drafter["id"]
                        discard, drafter_pos = get_snake_position(real_position+1)
                        for next_drafter in drafters:
                            if next_drafter["position"] == drafter_pos:
                                on_deck = next_drafter["id"]
                        discard, drafter_pos = get_snake_position(real_position+2)
                        for next_drafter in drafters:
                            if next_drafter["position"] == drafter_pos:
                                in_hole = next_drafter["id"]
                        msg = f"UP NOW: <@{now_up}>\nON DECK: <@{on_deck}>\nIN THE HOLE: <@{in_hole}>"
                        #log the current time
                        if draft_instance.time_limit_min > 0:
                            draft_instance.time_memory = time.time()
                        #schedule the send on the bot event loop from this worker thread
                        if getattr(draft_instance, "channel", None) is not None:
                            asyncio.run_coroutine_threadsafe(
                                draft_instance.channel.send(msg),
                                draft_instance.bot.loop
                            )
                    time.sleep(2)
                pass
    #print that the draft has finished
    asyncio.run_coroutine_threadsafe(
        draft_instance.channel.send("Draft has Finished."),
        draft_instance.bot.loop
    )
    #unbound the channel and reopen it for future drafts
    draft_instance.channel = None

#dictionary to store drafts
drafts = {} # key: draft_name, value: draft instance

"""
BOT EVENTS
    -on_ready (basically the bots constructor)
"""

#basically the bots constructor
@bot.event
async def on_ready():
    '''
    the function that functions as the bots constructor upon login and startup

    takes no parameters and returns nothing, instead declares and initializes various variables and data
    from saved files and such
    '''
    #tells the console the bot is logged in
    print(f'[BOT] Logged in as {bot.user}')
    #registering commands with discord
    try:
        synced = await bot.tree.sync()
        print(f"[BOT] Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"[BOT] Error syncing commands: {e}")
    #wipe the excels folder
    excel.wipe_excel_folder()
    print("[BOT] Excels File Refreshed.")
    #load the drafts from saved data
    print("[BOT] Loading Drafts from Save File...")
    try:
        with open ("drafts.csv", "r", newline='',encoding="utf-8") as draft_savefile:
            #helper function that turns "" into None
            def value_check(value):
                return None if value == "" else value
            #declare the reader and go through each line
            reader = csv.reader(draft_savefile)
            for row in reader:
                #get values from the csv
                draft_name = row[0]
                draft_rounds = int(value_check(row[2]))
                draft_limit = value_check(row[1])
                draft_sku = value_check(row[6])
                draft_seed = int(value_check(row[7]))
                current_position = int(value_check(row[8]))
                #creates the draft object
                new_draft = draft.Draft(draft_name, draft_rounds, draft_limit, draft_sku, bot, draft_seed, current_position)
                drafts[draft_name] = new_draft
                #gets the announcement id
                try:
                    new_draft.announcement_id = int(value_check(row[3]))
                except Exception:
                    new_draft.announcement_id = None
                new_draft.emoji = value_check(row[4])
                # restore announce channel id -> channel object if possible
                announce_id = value_check(row[5])
                if announce_id is None:
                    new_draft.announce_channel = None
                else:
                    try:
                        cid = int(announce_id)
                        # try cache first, fall back to API fetch
                        channel_obj = bot.get_channel(cid)
                        if channel_obj is None:
                            try:
                                channel_obj = await bot.fetch_channel(cid)
                            except Exception:
                                channel_obj = None
                        new_draft.announce_channel = channel_obj
                    except Exception:
                        new_draft.announce_channel = None
                print(f"[BOT] [FROM {draft_name.upper()}] Draft Loaded Successfully")
    except FileNotFoundError:
        print("[BOT] No Drafts to Load.")

"""
MISC AND TEST COMMANDS
    -bear (test command that sends a bear gif to make sure the bots working)
"""

#test command
@bot.tree.command(name="bear", description="sends a bear gif")
async def bear(interaction: discord.Interaction):
    await interaction.response.send_message("https://tenor.com/view/bear-scream-gif-7281540763674856279")


"""
ADMIN COMMANDS
    -create_draft (creates the draft, and its dedicated directory)
    -announce_draft (announces the draft and opens it for people to enter)
    -start_draft (starts the draft for everyone to star/get picking)
    -get_csv_file (returns a csv file for entire draft)
    -skip_turn (skips the current persons turn)
    -force_pick (forces a pick for the current user)
    -add_team ()
"""

#command that creates the draft
@bot.tree.command(name="create_draft", description="Creates the Draft")
async def create_draft(interaction: discord.Interaction,                       
    draft_object: str,
    draft_sku: str,
    draft_rounds: int,
    draft_limit: int = None
    ):
    '''
    function that takes in various parameters and creates a draft instance,
    primarily uses the robotevents API to gather team data from an event SKU

    :param draft_object: the name you want to assign to the draft
    :type draft_object: str
    :param draft_sku: the event sku to pull teams from
    :type draft_sku: str
    :param draft_rounds: the amount of rounds the draft will have
    :type draft_rounds: int
    :param draft_limit: the limit for the draft (optional field, defaults to None)
    :type draft_limit: int
    '''
    # permission check
    if not is_admin(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    #if the draft already exists, it will not create a duplicate
    if draft_object in drafts:
        print(f"[BOT] [FROM {draft_object}] Draft Already Exists")
        return
    #various input checkers
    if draft_rounds < 1:
        print(f"[BOT] [FROM {draft_object}] Invalid Amount of Rounds")
        return
    #creates the draft object
    new_draft = draft.Draft(draft_object, draft_rounds, draft_limit, draft_sku, bot)
    drafts[draft_object] = new_draft
    #acknowledge the interaction immediately to avoid token expiry while we do network/IO work
    await interaction.response.defer()
    #save the sku to the draft
    new_draft.draft_sku = draft_sku
    #send the draft creation confirmation
    msg = (
        f'Draft "{draft_object}" created successfully!\n'
        f'Rounds: {draft_rounds}\n'
        f'Teams Loaded: {len(new_draft.teams)}\n'
        f'Event SKU: {draft_sku}\n'
        f'Limit: {draft_limit}'
    )
    await interaction.followup.send(msg)
    #save the draft as is
    new_draft.save_draft()

#command to announce the draft
@bot.tree.command(name="announce_draft", description="Announces the Draft and opens it for people to enter")
async def announce_draft(interaction: discord.Interaction,
    draft_object: str,
    channel: discord.TextChannel,
    emoji_react: str
    ):
    '''
    function that announces the draft to a specified channel and opens it for people to enter

    :param draft_object: the name you want to assign to the draft
    :type draft_object: str
    :param channel: the discord text channel to announce the draft in
    :type channel: discord.TextChannel
    :param emoji_react: the emoji that people will react with to enter the draft (use standard emojis only)
    :type emoji_react: str
    '''
    # permission check
    if not is_admin(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    #send an initial message to the channel
    try:
        #acknowledge the interaction immediately to avoid token expiry while we do network/IO work
        await interaction.response.defer()
        announcement = await channel.send(f"The {drafts[draft_object].draft_name} draft is being announced! React with {emoji_react} to enter!")
        try:
            await announcement.add_reaction(emoji_react)

        #if there is an error with the emoji
        except discord.HTTPException:
            await interaction.followup.send(f"Improper Emoji Raised.",ephemeral=True)
            await announcement.delete()
            return
        #update the class
        drafts[draft_object].log_announcement(announcement.id,emoji_react,channel)
        #send the emoji in that channel
        print(f"[BOT] [FROM {drafts[draft_object].draft_name.upper()}] Draft announced in {channel}")
        #save the draft
        drafts[draft_object].save_draft()
    #if theres a channel restriction
    except discord.Forbidden:
        await interaction.followup.send(f"Bot does not have access to that channel.",ephemeral=True)
        return
    await interaction.followup.send(f"Draft Announced.")

#command to announce the draft
@bot.tree.command(name="start_draft", description="Starts the Draft")
async def start_draft(interaction: discord.Interaction,
    draft_object: str,
    draft_channel: discord.TextChannel,
    min_time_limit: int = 0,
    timer_warning: int = 5
    ):
    '''
    function that starts the draft instance, and creates a thread for the draft function to run in

    :param draft_object: the name you want to assign to the draft
    :type draft_object: str
    :param draft_channel: the discord text channel to start the draft in
    :type draft_channel: discord.TextChannel
    :param min_time_limit: the minimum time limit before a user is skipped (optional field, defaults to 0)
    :type min_time_limit: int
    :param timer_warning: the time before a warning is given (optional field, defaults to 0)
    :type min_time_limit: int
    '''
    await interaction.response.defer()
    #permission check
    if not is_admin(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return
    #get the emoji and announcement from the announcement message
    aid, emoji, channel = drafts[draft_object].get_announcement_id()
    announcment = await channel.fetch_message(aid)
    #get all of the users who reacted
    reaction = discord.utils.get(announcment.reactions, emoji=emoji)
    users = [user async for user in reaction.users() if not user.bot]
    player_data = [{"id":user.id,"name":user.name,"nick":user.nick or False}
    for user in users
    ]
    #generate the player data
    drafts[draft_object].generate_player_data(player_data)
    #set the draft order
    drafts[draft_object].set_draft_order()
    #create the draft excel file
    drafts[draft_object].excel_manager = excel.ExcelManager(f"{drafts[draft_object].draft_name}_draft", drafts[draft_object].draft_data,
                                                            drafts[draft_object].round_limit, drafts[draft_object].total_participants)
    drafts[draft_object].excel_manager.create_draft_sheet()
    #set the time limit
    drafts[draft_object].time_limit_min = min_time_limit
    drafts[draft_object].timer_warning = timer_warning
    #send an initial message to the channel
    try:
        await draft_channel.send(f"The {drafts[draft_object].draft_name} draft is starting soon!")
        #set the drafts communcations channel to the proper one
        drafts[draft_object].channel = draft_channel
        #start the thread
        thread_instance = threading.Thread(target=run_draft, args=(drafts[draft_object],bot), daemon=True)
        thread_instance.start()
    except discord.Forbidden:
        await interaction.followup.send(f"Bot does not have access to that channel.",ephemeral=True)
        return
    #respond to the user
    await interaction.followup.send(f"Draft Starting.")

#command to skip the current persons turn
@bot.tree.command(name="skip_turn", description="Skips the current drafters turn")
async def skip_turn(interaction: discord.Interaction):
    '''
    function that skips the turn of the draft assigned in the channel the command was sent in

    takes no parameters and returns nothing
    '''
    # permission check
    if not is_admin(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    #send an initial message to the channel
    try:
        #acknowledge the interaction immediately to avoid token expiry while we do network/IO work
        await interaction.response.defer()
        #validate what channel this draft is affilliated with, and set the skip check to true
        for draft in drafts:
            if drafts[draft].channel == interaction.channel:
                #get the current position, and the drafter id assigned
                current_position = drafts[draft].current_position
                for drafter in drafts[draft].draft_data:
                    if drafter["position"] == current_position:
                        drafter_id = drafter["id"]
                #update the skip check
                drafts[draft].skip_check = True
                print(f"[BOT] [FROM {drafts[draft].draft_name.upper()}] Requesting Turn Skip.")
                await interaction.followup.send(f"Skipping <@{drafter_id}>.")
                return
    #if theres a channel restriction
    except discord.Forbidden:
        await interaction.followup.send(f"Bot does not have access to that channel.",ephemeral=True)
        return
    await interaction.followup.send(f"Error.",ephemeral=True)

@bot.tree.command(name="get_csv_file", description="Returns a csv file for the draft")
async def get_csv_file(interaction: discord.Interaction,
    draft_object: str,
    ):
    '''
    function that returns a csv file of the draft from a draft object

    :param draft_object: the name of the requested draft
    :type draft_object: str
    '''
    # permission check
    if not is_admin(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    #send an initial message to the channel
    try:
        #acknowledge the interaction immediately to avoid token expiry while we do network/IO work
        await interaction.response.defer()
        draft_instance = drafts.get(draft_object)
        if not draft_instance:
            await interaction.followup.send("Draft does not exist.", ephemeral=True)
            return

        #gather and sort drafters by position
        drafters = getattr(draft_instance, "draft_data", []) or []
        sorted_drafters = sorted(drafters, key=lambda x: x.get("position", float("inf")))

        #write CSV to a temporary file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", newline="", encoding="utf-8")
        writer = csv.writer(tmp)
        #get the template row

        writer.writerow(["position", "id", "name", "picks"])

        for drafter in sorted_drafters:
            #get the position, name, and id
            pos = drafter["position"]
            d_id = drafter["id"]
            name = drafter["name"]
            #use draft_instance.get_picks to retrieve picks for that drafter
            try:
                picks = draft_instance.get_picks(d_id)
                for pick in picks:
                    pick = str(pick)
            except Exception:
                picks = None
            row = [pos ,d_id ,name]
            row.extend(picks)
            writer.writerow(row)

        tmp.flush()
        tmp.close()

        # Send the file and clean up
        with open(tmp.name, "rb") as fp:
            await interaction.followup.send(file=discord.File(fp, filename=f"{draft_object}_picks.csv"))
        os.remove(tmp.name)
        #send the emoji in that channel
        print(f"[BOT] [FROM {drafts[draft_object].draft_name.upper()}] CSV File Sent.")
        return
    #if theres a channel restriction
    except discord.Forbidden:
        await interaction.followup.send(f"Bot does not have access to that channel.",ephemeral=True)
        return

#function to force a pick upon a drafter
@bot.tree.command(name="force_pick", description="Force a pick for a drafter from a draft object")
async def force_pick(interaction: discord.Interaction,
    target: discord.User,
    pick: str,
    round: int = None
    ):
    '''
    function that forces a pick for a specified drafter during a draft

    :param target: the discord user to force the pick upon
    :type target: discord.User
    :param pick: the team to force the drafter to pick
    :type pick: str
    :param round: the round to force the pick in (optional field, defaults to None for current round)
    :type round: int
    '''
    #defer the response
    await interaction.response.defer()
    #permission check
    if not is_admin(interaction):
        await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
        return
    #check what channel they are in and get the discord user
    for draft in drafts:
        if drafts[draft].channel == interaction.channel:
            #this is the draft, validate the participant
            if drafts[draft].validate_participant(target.id) == True:
                #if the team is "random", pick a random team
                if pick == "random":
                    pick = drafts[draft].pick_random(target.id)
                    if not pick:
                        await interaction.followup.send(f"No Available Teams to Pick.",ephemeral=True)
                        return
                #if rounds is none, just add their pick to the queue
                if (round == None) or (round == drafts[draft].current_round):
                    if drafts[draft].pick_one(target.id,pick):
                        await interaction.followup.send(f"{pick} Chosen for <@{target.id}>",ephemeral=True)
                    else:
                        await interaction.followup.send(f"{pick} Does Not Exist.",ephemeral=True)
                    return
                else:
                    #will add this later
                    await interaction.followup.send(f"Command Not Implemented.",ephemeral=True)
                    return
            #if the target isnt a member of the draft
            await interaction.followup.send(f"Target is not a member of this draft.",ephemeral=True)
            return
    #if there is no draft to affiliate with
    await interaction.followup.send(f"Channel is not affiliated with a draft.",ephemeral=True)
    return

#function to force a pick upon a drafter
@bot.tree.command(name="add_team", description="Manually adds a team to the draft list")
async def add_team(interaction: discord.Interaction,
    team: str
    ):
    '''
    function that adds a team to the current draft instance

    :param team: the team to add to the draft
    :type team: str
    '''
    #defer the response
    await interaction.response.defer()
    #permission check
    if not is_admin(interaction):
        await interaction.followup.send("You do not have permission to use this command.", ephemeral=True)
        return
    #check what channel they are in and get the discord user
    for draft in drafts:
        if drafts[draft].channel == interaction.channel:
            if drafts[draft].add_team(team):
                await interaction.followup.send(f"{team} added to draft.",ephemeral=True)
            else:
                await interaction.followup.send("Team already exists.",ephemeral=True)
            return
    #if there is no draft to affiliate with
    await interaction.followup.send(f"Channel is not affiliated with a draft.",ephemeral=True)
    return

#function to force a pick upon a drafter
@bot.tree.command(name="remove_team", description="Manually removes a team to the draft list")
async def remove_team(interaction: discord.Interaction,
    team: str
    ):
    '''
    function that removes a team to the current draft instance

    :param team: the team to remove from the draft
    :type team: str
    '''
    #defer the response
    await interaction.response.defer()
    #permission check
    if not is_admin(interaction):
        await interaction.followup.send("You do not have permission to use this command.",ephemeral=True)
        return
    #check what channel they are in and get the discord user
    for draft in drafts:
        if drafts[draft].channel == interaction.channel:
            if drafts[draft].remove_team(team):
                await interaction.followup.send(f"{team} removed from draft.",ephemeral=True)
            else:
                await interaction.followup.send("Error while removing team.",ephemeral=True)
            return
    #if there is no draft to affiliate with
    await interaction.followup.send(f"Channel is not affiliated with a draft.",ephemeral=True)
    return

#function to set the downtime for the draft
@bot.tree.command(name="set_skip_downtime", description="Sets the downtime for the draft")
async def set_downtime(interaction: discord.Interaction, downtime_start: int, downtime_end: int):
    '''
    function that sets the downtime for the current draft instance

    :param downtime_start: the hour to start downtime (0-23)
    :type downtime_start: int
    :param downtime_end: the hour to end downtime (0-23)
    :type downtime_end: int
    '''
    #defer the response
    await interaction.response.defer()
    #permission check
    if not is_admin(interaction):
        await interaction.followup.send("You do not have permission to use this command.",ephemeral=True)
        return
    #check what channel they are in and get the discord user
    for draft in drafts:
        if drafts[draft].channel == interaction.channel:
            drafts[draft].set_downtime(downtime_start, downtime_end)
            await interaction.followup.send(f"Downtime set from {downtime_start}:00 to {downtime_end}:00.",ephemeral=True)
            return
    #if there is no draft to affiliate with
    await interaction.followup.send(f"Channel is not affiliated with a draft.",ephemeral=True)
    return

"""
USER COMMANDS
    -help (shows the user the available commands)
    -pick (add a single pick to your pick queue)
    -pick_multiple (add multiple picks to your pick queue)
    -pick_random (adds a random pick to your pick queue)
    -clear_picks (clears the picks from the user)
    -get_my_queue (shows the user their current queue of picks)
    -get_available_picks (shows the user all of the available picks)
"""

#command that shows the user all of the available commands
@bot.tree.command(name="help", description="Shows the available commands")
async def help(interaction: discord.Interaction):
    '''
    function that shows the user all of the available commands

    takes no parameters and returns nothing
    '''
    help_msg = (
        "**Available Commands:**\n"
        "/pick [team]: Add a single pick to your pick queue.\n"
        "/pick_multiple [team1] [team2] [team3] [team4]: Add multiple picks (up to 4) to your pick queue.\n"
        "/pick_random: Adds a random pick to your pick queue.\n"
        "/clear_picks: Clears any picks that you currently have in queue.\n"
        "/get_my_picks: Gets what current picks you have that have been processed.\n"
        "/get_my_queue: Shows your current picks that are in your queue.\n"
        "/get_available_picks: Shows all of the available picks."
    )
    await interaction.response.send_message(help_msg, ephemeral=True)

#command that lets the user pick one bot
@bot.tree.command(name="pick", description="add a single pick to your pick queue")
async def pick(interaction: discord.Interaction, team: str):
    '''
    function that allows the user to pick a single team to add to their pick queue

    :param team: the team to add to the queue
    :type team: str
    '''
    #upper the pick
    team = team.upper()
    #check what channel this draft is affilliated with
    passed,draft = validation_check(interaction)
    if passed:
        #put the pick in their queue
        if drafts[draft].pick_one(interaction.user.id,team):
            await interaction.response.send_message(f"{team} Chosen.",ephemeral=True)
        else:
            await interaction.response.send_message(f"{team} is not available.")
        return
    await interaction.response.send_message("You do not have permission to use this command.",ephemeral=True)

#command that lets the user reserve multiple picks (up to 4) so the bot can automatically pick for them
@bot.tree.command(name="pick_multiple", description="Lets you select a multitude of teams (max of 4) to be queued")
async def pick_multiple(interaction: discord.Interaction,
    team1: str,
    team2: str = None,
    team3: str = None,
    team4: str = None
    ):
    '''
    function that allows the user to pick a multiple teams to add to their pick queue

    :param team1: the first team to add to the queue
    :type team1: str
    :param team2: the second team to add to the queue (optional field, defaults to None)
    :type team2: str
    :param team3: the third team to add to the queue (optional field, defaults to None)
    :type team3: str
    :param team4: the fourth team to add to the queue (optional field, defaults
    :type team4: str
    '''
    #create a list to send to the function
    picks = []
    #goes through one by one
    picks.append(team1.upper()) if isinstance(team1, str) else None
    picks.append(team2.upper()) if isinstance(team2, str) else None
    picks.append(team3.upper()) if isinstance(team3, str) else None
    picks.append(team4.upper()) if isinstance(team4, str) else None
    #deletes none if it exists
    for pick in picks:
        if pick == None:
            picks.remove(pick)
    passed,draft = validation_check(interaction)
    if passed:
        #put the pick in their queue
        completed = drafts[draft].pick_multiple(interaction.user.id, picks)
        if completed:
            await interaction.response.send_message(f"{picks} Chosen.", ephemeral=True)
        else:
            await interaction.response.send_message("Teams or Player is not available.", ephemeral=True)
        return
    await interaction.response.send_message("You do not have permission to use this command.",ephemeral=True)

#command that lets the user pick a random available team
@bot.tree.command(name="pick_random", description="Adds a random pick to your pick queue.")
async def pick_random(interaction: discord.Interaction):
    '''
    function that allows the user to pick a random team to add to their pick queue

    takes no parameters and returns nothing
    '''
    #check what channel this draft is affilliated with
    passed,draft = validation_check(interaction)
    if passed:
        #put the pick in their queue
        team = drafts[draft].pick_random(interaction.user.id)
        if team:
            await interaction.response.send_message(f"{team} Chosen.",ephemeral=False)
        else:
            await interaction.response.send_message(f"No Available Teams to Pick. (oh no, contact bor admin)",ephemeral=False)
        return    
    await interaction.response.send_message(f"You do not have permission to use this command.",ephemeral=True)

#command that lets the user clear their list of picks
@bot.tree.command(name="clear_picks", description="Clears any picks that you currently have in queue.")
async def clear_picks(interaction: discord.Interaction):
    '''
    function that allows the user to clear their picks

    takes no parameters and returns nothing
    '''
    #check what channel this draft is affilliated with
    passed,draft = validation_check(interaction)
    if passed:
        #code here
        if drafts[draft].clear_picks(interaction.user.id):
            await interaction.response.send_message(f"Picks Cleared",ephemeral=True)
        else:
            await interaction.response.send_message(f"Error While Clearing Picks",ephemeral=True)
        return    
    await interaction.response.send_message(f"You do not have permission to use this command.",ephemeral=True)

#command that shows the user their current picks
@bot.tree.command(name="get_my_picks", description="Gets what current picks you have.")
async def get_my_picks(interaction: discord.Interaction):
    '''
    function that allows the user to see what picks they currently have

    takes no parameters and returns nothing
    '''
    #check what channel this draft is affilliated with
    passed,draft = validation_check(interaction)
    if passed:
        #check the picks from the draft
        picks = drafts[draft].get_picks(interaction.user.id)
        await interaction.response.send_message(f"Your current picks are {picks}.")
        return
    await interaction.response.send_message(f"You do not have permission to use this command.",ephemeral=True)

#command that shows the user their current queue
@bot.tree.command(name="get_my_queue", description="Shows your current picks that are in your queue.")
async def get_my_queue(interaction: discord.Interaction):
    '''
    function that allows the user to see what picks are currently in their queue

    takes no parameters and returns nothing
    '''
    passed,draft = validation_check(interaction)
    if passed:
        #get the picks
        picks = drafts[draft].get_queue(interaction.user.id)
        await interaction.response.send_message(f"Your current queue is {picks}")
        return    
    await interaction.response.send_message(f"You do not have permission to use this command.",ephemeral=True)

#command that shows the user all of the available picks
@bot.tree.command(name="get_available_picks", description="Tells user what picks they have available.")
async def get_available_picks(interaction: discord.Interaction):
    '''
    function that allows the user to see what picks are available

    takes no parameters and returns nothing
    '''
    #get what channel command was sent in, and the user id
    passed,draft = validation_check(interaction)
    if passed:
        #make a new list of team strings so we don't mutate the draft's internal list
        picks = [str(p) for p in list(drafts[draft].get_teams())]
        #remove the picks that have 0 remaining picks
        for team in list(picks):
            if drafts[draft].teams.get(team, 0) == 0:
                picks.remove(team)
        #embed function for teams
        def team_embed(items, page, total_pages):
            embed = discord.Embed(
                title=f"Available Teams (Page {page + 1}/{total_pages})",
                description="\n".join(items),
                color=discord.Color.green()
            )
            return embed
        #declare the paginator and send the message
        paginator = Paginator(picks, per_page=10, embed_fn=team_embed)
        await interaction.response.send_message(
            embed=team_embed(picks[:10], 0, (len(picks)-1)//10 + 1),
            view=paginator,
            ephemeral=True
        )
        return
    await interaction.response.send_message(f"You do not have permission to use this command.",ephemeral=True)

#command that shows the user all of the available picks
@bot.tree.command(name="get_draft_image", description="Shows the user an image of the current draft.")
async def get_draft_image(interaction: discord.Interaction):
    '''
    function that sends the user an image of the current draft

    takes no parameters and returns nothing
    '''
    #get what channel command was sent in, and the user id
    passed,draft = validation_check(interaction)
    if passed:
        #send an initial message to the channel
        try:
            #acknowledge the interaction immediately to avoid token expiry while we do network/IO work
            await interaction.response.defer()
            draft_instance = drafts.get(draft)
            if not draft_instance:
                await interaction.followup.send("Draft does not exist.", ephemeral=True)
                return
            #update the excel file
            draft_instance.excel_manager.fill_draft_sheet(draft_instance.draft_data)
            #get an image of the draft sheet
            image_path = draft_instance.excel_manager.get_draft_as_image()
            #send the image
            await interaction.followup.send(file=discord.File(image_path))
            #delete the temporary image file
            os.remove(image_path)
            #send the emoji in that channel
            print(f"[BOT] [FROM {drafts[draft].draft_name.upper()}] Image Sent.")
            return
        #if theres a channel restriction
        except discord.Forbidden:
            await interaction.followup.send(f"Bot does not have access to that channel.",ephemeral=True)
            return
    await interaction.response.send_message(f"You do not have permission to use this command.",ephemeral=True)


#runs the bot on the token (very important yes very hmmm)
bot.run(DS_TOKEN)