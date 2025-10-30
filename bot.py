"""
File: bot.py
Author: Jeremiah Nairn

Description: This is a fantasy draft bot built specificly for vex and robotevents.
"""

"""
CHECKLIST/ORDER OF COMPLETION
MS 1: DRAFT REGISTRATION (COMPLETE)
MS 2: PEOPLE DATA COLLECTION (COMPLETE)
MS 3: AUTOMATE INITIAL DATA COLLECTION (COMPLETE)
MS 4: MAIN DRAFT FUNCTIONALITY (COMPLETE)
MS 5: AUTOMATE DRAFT RESULTS
    -when the draft is finished draft admins can send a command for the bot to compute the draft results based on parameters
    -if the data is incomplete, it will error
    -if not, it will send an image of the CSV data or send the file itself
    -also will possibly just list the results in text
MS 6: QUALITY OF LIFE CHANGES
    -add an optional time limit for the bot to skip over people, skipped people can pick later but only at first come first serve
    -automated draft results will be placed in a cleaner excel file to look better
"""

#import draft
from manager import draft
#import robotevents
from manager import robotevents_handler

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
"""

class Pagination(discord.ui.View):
    def __init__(self, pages: list[str], timeout: int = 180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0

    async def update_message(self, interaction: discord.Interaction):
        content = self.pages[self.current_page]
        await interaction.response.edit_message(content=content, view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_message(interaction)


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
    #get the draft order
    drafters = draft_instance.draft_data
    #set the draft order
    draft_instance.set_draft_order()
    reverse = 1
    #go through each round
    for round in range(draft_instance.round_limit):
        #increases the round
        draft_instance.current_round +=1
        #goes through each position
        for position in range(draft_instance.total_participants):
            #validate who is supposed to be up for this turn
            for drafter in drafters:
                if drafter["position"] == draft_instance.current_position:
                    #debouncer
                    debounce = True
                    #check and see if their queue can be processed
                    while not draft_instance.process_pick(draft_instance.current_position):
                        #check if skip has been requested
                        if draft_instance.skip_check:
                            draft_instance.skip_check = False
                            print(f"[BOT] [FROM {draft_instance.draft_name}] Turn Skipped.")
                            break
                        # ping who is up, who is on deck, and who is in the hole (only once per turn)
                        if debounce:
                            debounce = False
                            try:
                                #map positions to drafter ids
                                pos_map = {d.get("position"): d.get("id") for d in drafters}
                                total = draft_instance.total_participants or len(pos_map)
                                curr = draft_instance.current_position
                                direction = reverse  # 1 for forward, -1 for backward
                                #helper to safely mention a position
                                def mention_for_pos(p):
                                    _id = pos_map.get(p)
                                    return f"<@{_id}>" if _id else ""
                                #compute next two pick positions using the same increment logic as the loop
                                if position + 1 == total:
                                    # we're at the end of the current pass: next pick is the same position (start of next pass),
                                    # then one position inward from the end on the next pass
                                    next1_pos = curr
                                    next2_pos = curr - 1 if total > 1 else curr
                                else:
                                    #normal case: next is current + direction
                                    next1_pos = curr + direction
                                    #if the following index would be the last in this pass, the pick after next1 will be the same (start of next pass)
                                    if position + 2 == total:
                                        next2_pos = next1_pos
                                    else:
                                        next2_pos = next1_pos + direction
                                #clamp positions to valid range [1, total]
                                def clamp(p):
                                    if p is None: 
                                        return None
                                    return max(1, min(total, p))
                                next1_pos = clamp(next1_pos)
                                next2_pos = clamp(next2_pos)
                                now_up = mention_for_pos(curr)
                                on_deck = mention_for_pos(next1_pos)
                                in_hole = mention_for_pos(next2_pos)

                                msg = f"UP NOW: {now_up}\nON DECK: {on_deck}\nIN THE HOLE: {in_hole}"
                                # schedule the send on the bot event loop from this worker thread
                                if getattr(draft_instance, "channel", None) is not None:
                                    asyncio.run_coroutine_threadsafe(
                                        draft_instance.channel.send(msg),
                                        draft_instance.bot.loop
                                    )
                            except Exception as e:
                                print(f"[BOT] Error sending draft ping: {e}")
                        time.sleep(1)
                    pass
            draft_instance.current_position += (0 if position+1 == draft_instance.total_participants else 1*reverse)
        reverse = reverse*-1
    #print that the draft has finished
    asyncio.run_coroutine_threadsafe(
        draft_instance.channel.send("Draft has Finished."),
        draft_instance.bot.loop
    )
    #unbound the channel and reopen it for future drafts
    draft_instance.channel = None

#dictionary to store drafts
drafts = {} # key: draft_name, value: draft instance
draft_apidata = {} #key: draft_name, value: draft instance that refers to the robotevents side

"""
BOT EVENTS
    -on_ready (basically the bots constructor)
"""

#basically the bots constructor
@bot.event
async def on_ready():
    #tells the console the bot is logged in
    print(f'[BOT] Logged in as {bot.user}')
    #registering commands with discord
    try:
        synced = await bot.tree.sync()
        print(f"[BOT] Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"[BOT] Error syncing commands: {e}")
    #load the drafts from saved data
    with open ("drafts.csv", "r", newline='',encoding="utf-8") as draft_savefile:
        #helper function that turns "" into None
        def value_check(value):
            return None if value == "" else value
        #declare the reader and go through each line
        reader = csv.reader(draft_savefile)
        for row in reader:
            draft_name = row[0]
            draft_rounds = int(value_check(row[2]))
            draft_limit = value_check(row[1])
            draft_sku = value_check(row[6])
            #creates the draft object
            new_draft = draft.Draft(draft_name, draft_rounds, draft_limit, bot)
            drafts[draft_name] = new_draft
            #creates the robotevents object
            new_api = robotevents_handler.Robotevent(draft_name,draft_sku, RB_TOKEN)
            draft_apidata[draft_name] = new_api
            #generates the team data
            draft_teams = new_api.get_teams_from_event()
            new_draft.generate_team_data(draft_teams,draft_rounds)
            #gets the announcement id
            new_draft.announcement_id = int(value_check(row[3]))
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

"""
MISC AND TEST COMMANDS
    -bear (test command that sends a bear gif to make sure the bots working)
    -get_teams (creates a temporary API object and prints a list of teams to make sure the API request is working)
"""

#test command
@bot.tree.command(name="bear", description="sends a bear gif")
async def bear(interaction: discord.Interaction):
    await interaction.response.send_message("https://tenor.com/view/bear-scream-gif-7281540763674856279")

#command that lets the user clear their list of picks
@bot.tree.command(name="get_teams", description="Gives you a list of teams from a certain event.")
async def get_teams(interaction: discord.Interaction,
    sku: str
    ):
    await interaction.response.defer()
    rbh = robotevents_handler.Robotevent("get_teams_command",sku, RB_TOKEN)
    teams = rbh.get_teams_from_event()
    await interaction.followup.send(f"{teams}")

"""
ADMIN COMMANDS
    -create_draft (creates the draft, and its dedicated directory)
    -announce_draft (announces the draft and opens it for people to enter)
    -start_draft (starts the draft for everyone to star/get picking)
    -get_all_picks (returns a csv file for entire draft)
    -skip (skips the current persons turn)
"""

#command that creates the draft
@bot.tree.command(name="create_draft", description="Creates the Draft")
async def create_draft(interaction: discord.Interaction,
    draft_object: str,
    draft_sku: str,
    draft_rounds: int,
    draft_limit: int = None
    ):
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
    new_draft = draft.Draft(draft_object, draft_rounds, draft_limit, bot)
    drafts[draft_object] = new_draft
    #acknowledge the interaction immediately to avoid token expiry while we do network/IO work
    await interaction.response.defer()
    #save the sku to the draft
    new_draft.draft_sku = draft_sku
    #creates the robotevents object and gets the teams
    new_api = robotevents_handler.Robotevent(draft_object,draft_sku, RB_TOKEN)
    draft_apidata[draft_object] = new_api
    draft_teams = new_api.get_teams_from_event()
    new_draft.generate_team_data(draft_teams,draft_rounds)
    #safely compute teams count and send the final followup (we already deferred)
    try:
        if draft_teams is None:
            teams_count = 0
        elif hasattr(draft_teams, "__len__"):
            teams_count = len(draft_teams)
        else:
            # if it's an iterator/generator, convert to list (be cautious with very large datasets)
            draft_teams = list(draft_teams)
            teams_count = len(draft_teams)
    except Exception:
        teams_count = 0
    #send the draft creation confirmation
    msg = (
        f'Draft "{draft_object}" created successfully!\n'
        f'Rounds: {draft_rounds}\n'
        f'Teams Loaded: {teams_count}\n'
        f'Event ID: {new_api.get_event_id()}\n'
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
    min_time_limit: int = None
    ):
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
    player_data = [
    {
        "id":user.id,
        "name":user.name,
        "nick":user.nick or False
    }
    for user in users
    ]
    #generate the player data
    drafts[draft_object].generate_player_data(player_data)
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

#command to get a csv file of the current draft
#note: this command will eventually be reworked to an excel file, and made available for all users
@bot.tree.command(name="get_csv_file", description="Returns a csv file for the draft")
async def get_csv_file(interaction: discord.Interaction,
    draft_object: str,
    ):
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
            pos = drafter.get("position", "")
            did = drafter.get("id", "")
            name = drafter.get("name", "")
            #use draft_instance.get_picks to retrieve picks for that drafter
            try:
                picks = draft_instance.get_picks(did)
                for pick in picks:
                    pick = str(pick)
            except Exception:
                picks = None
            row = [pos ,did ,name]
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
    #if theres a channel restriction
    except discord.Forbidden:
        await interaction.followup.send(f"Bot does not have access to that channel.",ephemeral=True)
        return
    await interaction.followup.send(f"CSV File Sent.")

#command to skip the current persons turn
@bot.tree.command(name="skip_turn", description="Skips the current drafters turn")
async def skip_turn(interaction: discord.Interaction):
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

"""
USER COMMANDS
    -quick_pick (reserves a single pick for the next turn)
    -queue_picks (reserves multiple picks so the bot can automatically pick from it)
    -clear_picks (clears the picks from the user)
    -get_my_queue (shows the user their current queue of picks)
    -get_available_picks (shows the user all of the available picks)
"""

#command that lets the user pick one bot
    #1 mandatory parameter for team pick
@bot.tree.command(name="quick_pick", description="Reserve a single pick for your next turn")
async def quick_pick(interaction: discord.Interaction, team: str):
    #upper the pick
    team = team.upper()
    #check what channel this draft is affilliated with
    passed,draft = validation_check(interaction)
    if passed:
        #put the pick in their queue
        if drafts[draft].pick_one(interaction.user.id,team):
            await interaction.response.send_message(f"{team} Chosen.")
        else:
            await interaction.response.send_message(f"{team} Does Not Exist.")
        return
    await interaction.response.send_message("You do not have permission to use this command.",ephemeral=True)

#command that lets the user reserve multiple picks (up to 4) so the bot can automatically pick for them
    #1 mandatory parameter for double picking teams
    #1 mandatory parameter for team pick
    #3 optional team pick parameters
@bot.tree.command(name="queue_picks", description="Lets you select a multitude of teams (max of 4) to be queued")
async def queue_picks(interaction: discord.Interaction,
    team1: str,
    team2: str = None,
    team3: str = None,
    team4: str = None
    ):
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
        completed = drafts[draft].pick_multiple(interaction.user.id,picks)
        await interaction.response.send_message(f"{picks} Chosen.",ephemeral=True if completed else "Teams or Player does not exist.")
        return
    await interaction.response.send_message("You do not have permission to use this command.",ephemeral=True)

#command that lets the user clear their list of picks
@bot.tree.command(name="clear_picks", description="Clears any picks that you currently have in queue.")
async def clear_picks(interaction: discord.Interaction):
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

@bot.tree.command(name="get_my_picks", description="Gets what current picks you have.")
async def get_my_picks(interaction: discord.Interaction):
    #check what channel this draft is affilliated with
    passed,draft = validation_check(interaction)
    if passed:
        #check the picks from the draft
        picks = drafts[draft].get_picks(interaction.user.id)
        await interaction.response.send_message(f"Your current picks are {picks}.")
        return
    await interaction.response.send_message(f"You do not have permission to use this command.",ephemeral=True)

#command that shows the user their current picks
@bot.tree.command(name="get_my_queue", description="Shows your current picks that are in your queue.")
async def get_my_queue(interaction: discord.Interaction):
    passed,draft = validation_check(interaction)
    if passed:
        #get the picks
        picks = drafts[draft].get_queue(interaction.user.id)
        await interaction.response.send_message(f"You have Picked {picks}")
        return    
    await interaction.response.send_message(f"You do not have permission to use this command.",ephemeral=True)

#command that shows the user all of the available picks
@bot.tree.command(name="get_available_picks", description="Tells user what picks they have available.")
async def get_available_picks(interaction: discord.Interaction):
    #get what channel command was sent in, and the user id
    passed,draft = validation_check(interaction)
    if passed:
        #make an index to create new pages for every 8 teams
        index = 1
        #get all of the available picks and send them
        team_msg = "The Current Teams Are:\n"
        for team in drafts[draft].teams:
            team_msg += f"{team["team"]}, {team["picks_remaining"]} Left\n" if team["picks_remaining"] != 0 else ""
        #send this monster of a message
        await interaction.response.send_message(team_msg,ephemeral=True)
        return    
    await interaction.response.send_message(f"You do not have permission to use this command.",ephemeral=True)

#runs the bot on the token
bot.run(DS_TOKEN)