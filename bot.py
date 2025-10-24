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
MS 4: MAIN DRAFT FUNCTIONALITY
    -draft bot will create a thread to run through the draft depending on how many rounds
    -
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


#discord imports
import discord
from discord import app_commands
from discord.ext import commands

#setup intents (just message_content isn't needed for slash commands, but safe to keep)
intents = discord.Intents.default()
intents.reactions = True
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

#assigns "!" as the command prefix for all commands
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

#admin bypass id (allowed even if not an actual server administrator)
ADMIN_BYPASS_IDS = [453273679095136286]

"""
HELPER FUNCTIONS
    -is_admin (checks of the user is an admin)
    -validation_check(checks if the user is in the draft and in the correct channel)
"""

#function to return true if the user is an administator, false if not
def is_admin(interaction: discord.Interaction) -> bool:
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

def validation_check(drafter_id, drafter_channel) -> bool:
    for draft in drafts:
        if drafts[draft].channel == drafter_channel:
            #validate and make sure person is in the draft
            if drafts[draft].validate_participant(drafter_id) == True:
                #code here
                return True, draft
    return False, None

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
    rbh = robotevents_handler.Robotevent("get_teams_command",sku, RB_TOKEN)
    teams = rbh.get_teams_from_event()
    await interaction.response.send_message(f"{teams}")

"""
ADMIN COMMANDS
    -create_draft (creates the draft, and its dedicated directory)
    -announce_draft (announces the draft and opens it for people to enter)
    -setup_draft (creates and obtains the last bit of data needed for the draft to function)
    -start_draft (starts the draft for everyone to start picking)
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
    new_draft = draft.Draft(draft_object, draft_rounds, draft_limit)
    drafts[draft_object] = new_draft
    #acknowledge the interaction immediately to avoid token expiry while we do network/IO work
    await interaction.response.defer()
    #creates the robotevents object
    new_api = robotevents_handler.Robotevent(draft_object,draft_sku, RB_TOKEN)
    draft_apidata[draft_object] = new_api
    #gets a list of teams for that event, and puts it into a csv file
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

    msg = (
        f'Draft "{draft_object}" created successfully!\n'
        f'Rounds: {draft_rounds}\n'
        f'Teams Loaded: {teams_count}\n'
        f'Event ID: {new_api.get_event_id()}\n'
        f'Event SKU: {draft_sku}\n'
        f'Limit: {draft_limit}'
    )

    await interaction.followup.send(msg)

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
        print("message printed (bogos binted)")
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
        print(f"[BOT] [FROM {drafts[draft_object].draft_name}] Draft starting in {drafts[draft_object].channel}")
    except discord.Forbidden:
        await interaction.followup.send(f"Bot does not have access to that channel.",ephemeral=True)
        return
    #respond to the user
    await interaction.followup.send(f"Draft Starting.")
"""
USER COMMANDS
    -pick (reserves a single pick for the next turn)
    -reserve_picks (reserves multiple picks so the bot can automatically pick from it)
    -clear_pick (clears the picks from the user)
    -draft_status (checks the status of the current draft)
"""

#command that lets the user pick one bot
    #1 mandatory parameter for team pick
@bot.tree.command(name="pick", description="Reserve a Single Pick for your next turn")
async def pick(interaction: discord.Interaction, team: str):
    #upper the pick
    team = team.upper()
    #get what channel command was sent in, and the user id
    drafter_id = interaction.user.id
    drafter_channel = interaction.channel
    #check what channel this draft is affilliated with
    passed,draft = validation_check(drafter_id,drafter_channel)
    if passed:
        #put the pick in their queue
        completed = drafts[draft].pick_one(drafter_id,team)
        await interaction.response.send_message(f"{team} Chosen." if completed else "Team or Player does not exist.",ephemeral=True)
        return
    await interaction.response.send_message("You do not have permission to use this command.",ephemeral=True)

#command that lets the user reserve multiple picks (up to 4) so the bot can automatically pick for them
    #1 mandatory parameter for double picking teams
    #1 mandatory parameter for team pick
    #3 optional team pick parameters
@bot.tree.command(name="reserve_picks", description="Lets you select a multitude of teams (max of 4)")
async def reserve_picks(interaction: discord.Interaction,
    doublepick: bool,
    team1: str,
    team2: str = None,
    team3: str = None,
    team4: str = None
    ):
    #get what channel command was sent in, and the user id
    drafter_id = interaction.user.id
    drafter_channel = interaction.channel
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
    passed,draft = validation_check(drafter_id,drafter_channel)
    if passed:
        #put the pick in their queue
        completed = drafts[draft].pick_multiple(drafter_id,picks,doublepick)
        await interaction.response.send_message(f"{picks} Chosen." if completed else "Teams or Player does not exist.",ephemeral=True)
        return
    await interaction.response.send_message("You do not have permission to use this command.",ephemeral=True)

#command that lets the user clear their list of picks
@bot.tree.command(name="clear_picks", description="Clears any picks that you currently have.")
async def clear_picks(interaction: discord.Interaction):
    #get what channel command was sent in, and the user id
    drafter_id = interaction.user.id
    drafter_channel = interaction.channel
    #check what channel this draft is affilliated with
    passed,draft = validation_check(drafter_id,drafter_channel)
    if passed:
        #code here
        if drafts[draft].clear_picks(drafter_id):
            await interaction.response.send_message(f"Picks Cleared",ephemeral=True)
        else:
            await interaction.response.send_message(f"Error While Clearing Picks",ephemeral=True)
        return    
    await interaction.response.send_message(f"You do not have permission to use this command.",ephemeral=True)

#command that shows the user their current picks
@bot.tree.command(name="show_picks", description="Shows your current picks")
async def show_picks(interaction: discord.Interaction):
    #get what channel command was sent in, and the user id
    drafter_id = interaction.user.id
    drafter_channel = interaction.channel
    passed,draft = validation_check(drafter_id,drafter_channel)
    if passed:
        #get the picks
        picks = drafts[draft].get_queue(drafter_id)
        await interaction.response.send_message(f"You have Picked {picks}",ephemeral=True)
        return    
    await interaction.response.send_message(f"You do not have permission to use this command.",ephemeral=True)

#command to tell people whos currently supposed to be picking
@bot.tree.command(name="whos_up", description="Tells the user who is currently supposed to be picking.")
async def whos_up(interaction: discord.Interaction):
    #get what channel command was sent in, and the user id
    drafter_id = interaction.user.id
    drafter_channel = interaction.channel
    passed,draft = validation_check(drafter_id,drafter_channel)
    if passed:
        #code here
        await interaction.response.send_message(f"Command Not Yet Implemented",ephemeral=True)
        return    
    await interaction.response.send_message(f"You do not have permission to use this command.",ephemeral=True)

#runs the bot on the token
bot.run(DS_TOKEN)