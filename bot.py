"""
File: bot.py
Author: Jeremiah Nairn

Description: This is a fantasy draft bot built specificly for vex and robotevents.
"""

"""
CHECKLIST/ORDER OF COMPLETION
MS 1: DRAFT REGISTRATION
    -draft admins should be able to start a draft using a single command with parameters
    -bot will then make a directory for each draft for that data to be stored
    -then the bot will announce the draft (somewhere) and use a reaction emoji for people to register
    -registered people will then be logged into a CSV file where their picks will be stored in the future
MS 2: MAIN DRAFT DATA MANIPULATION
    -add a command to queue/select a pick
    -add a similar command that backlogs your picks and will automatically pick for you based on whats available
    -prompt users when they are 1-3 places in the queue to pick
    -log their picks in the csv file
    -when the
MS 3: AUTOMATE INITIAL DATA COLLECTION
    -import the robotevents api and use it to get a list of teams
MS 4: AUTOMATE DRAFT RESULTS
    -when the draft is finished draft admins can send a command for the bot to compute the draft results based on parameters
    -if the data is incomplete, it will error
    -if not, it will send an image of the CSV data or send the file itself
    -also will possibly just list the results in text
MS 5: QUALITY OF LIFE CHANGES
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
    new_draft.generate_team_csv(draft_teams,draft_rounds)
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

#command to set up the player csv file
@bot.tree.command(name="setup_draft", description="Creates a CSV file with everyone who reacted using the announcement emoji.")
async def setup_draft(interaction: discord.Interaction,
    draft_object: str
    ):
    #get the emoji and announcement
    aid, emoji, channel = drafts[draft_object].get_announcement_id()
    announcment = await channel.fetch_message(aid)
    #get all of the users who reacted
    reaction = discord.utils.get(announcment.reactions, emoji=emoji)
    users = [user async for user in reaction.users() if not user.bot]
    player_data = [
    [
        user.id,
        user.name,
        user.nick or False
    ]
    for user in users
    ]
    drafts[draft_object].generate_player_csv(player_data)
    await interaction.response.send_message(f"Command Not Yet Implemented",ephemeral=True)

#command to announce the draft
@bot.tree.command(name="start_draft", description="Starts the Draft")
async def start_draft(interaction: discord.Interaction,
    draft_object: str,
    draft_channel: discord.TextChannel,
    min_time_limit: int = None
    ):
    #send an initial message to the channel
    try:
        await draft_channel.send(f"The {drafts[draft_object].draft_name} draft is starting soon!")
        #set the drafts communcations channel to the proper one
        drafts[draft_object].channel = draft_channel
        print(f"{drafts[draft_object].draft_name} draft starting in {drafts[draft_object].channel}")
    except discord.Forbidden:
        await interaction.response.send_message(f"Bot does not have access to that channel.",ephemeral=True)
        return
    #respond to the user
    await interaction.response.send_message(f"Command Not Yet Fully Implemented",ephemeral=True)
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
    await interaction.response.send_message(f"Command Not Yet Implemented",ephemeral=True)

#command that lets the user reserve multiple picks (up to 4) so the bot can automatically pick for them
    #1 mandatory parameter for double picking teams
    #1 mandatory parameter for team pick
    #3 optional team pick parameters
@bot.tree.command(name="reserve_picks", description="Lets you select a multitude of teams for the bot to automaticly pick for you")
async def reserve_picks(interaction: discord.Interaction,
    doublepick: bool,
    team1: str,
    team2: str = None,
    team3: str = None,
    team4: str = None
    ):
    await interaction.response.send_message(f"Command Not Yet Implemented",ephemeral=True)

#command that lets the user clear their list of picks
@bot.tree.command(name="clear_picks", description="Clears any picks that you currently have.")
async def clear_picks(interaction: discord.Interaction):
    await interaction.response.send_message(f"Command Not Yet Implemented",ephemeral=True)

#command that lets the user clear their list of picks
@bot.tree.command(name="draft_status", description="Tells the user the current draft status.")
async def draft_status(interaction: discord.Interaction):
    await interaction.response.send_message(f"Command Not Yet Implemented",ephemeral=True)


#runs the bot on the token
bot.run(DS_TOKEN)