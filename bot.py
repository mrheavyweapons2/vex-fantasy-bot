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
intents.message_content = True

#assigns "!" as the command prefix for all commands
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())





#dictionary to store drafts
drafts = {} # key: draft_name, value: Draft instance



#basically the bots constructor
@bot.event
async def on_ready():
    #tells the console the bot is logged in
    print(f'Logged in as {bot.user}')
    #registering commands with discord
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")


"""
MISC COMMANDS
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
    -start_draft (starts the draft for everyone to start picking)
"""

#command that creates the draft
@bot.tree.command(name="create_draft", description="Creates the Draft")
async def create_draft(interaction: discord.Interaction,
    draft_object: str,
    draft_rounds: int,
    draft_limit: int = None
    ):
    #if the draft already exists, it will not create a duplicate
    if draft_object in drafts:
        await interaction.response.send_message(f'A draft named "{draft_object}" already exists!', ephemeral=True)
        return
    #various input checkers
    if draft_rounds < 1:
        await interaction.response.send_message(f'Invalid amount of rounds.', ephemeral=True)
        return
    #creates the draft object
    new_draft = draft.Draft(draft_object, draft_rounds, draft_limit)
    drafts[draft_object] = new_draft
    #sends the draft creator the draft information
    await interaction.response.send_message(
        f'{draft_rounds} Round Draft "{draft_object}" created with {f"a limit of {draft_limit} people" if draft_limit else 'no limit'}')

#command to announce the draft
@bot.tree.command(name="announce_draft", description="Announces the Draft and opens it for people to enter")
async def announce_draft(interaction: discord.Interaction,
    draft_object: str,
    channel: discord.TextChannel,
    emoji_react: str
    ):

    #send an initial message to the channel
    try:
        announcement = await channel.send(f"The {drafts[draft_object].draft_name} draft is being announced! React with {emoji_react} to enter!")
        print("message printed (bogos binted)")
        try:
            await announcement.add_reaction(emoji_react)
        #if there is an error with the emoji
        except discord.HTTPException:
            await interaction.response.send_message(f"Improper Emoji Raised.",ephemeral=True)
            await announcement.delete()
            return
        print(emoji_react)
        #set the drafts communcations channel to the proper one
        drafts[draft_object].channel = channel
        print(f"{drafts[draft_object].draft_name} draft announced in {drafts[draft_object].channel}")
    #if theres a channel restriction
    except discord.Forbidden:
        await interaction.response.send_message(f"Bot does not have access to that channel.",ephemeral=True)
        return
    await interaction.response.send_message(f"Command Not Yet Implemented",ephemeral=True)

#command to set up the player csv file
@bot.tree.command(name="setup_draft", description="Creates a CSV file with everyone who reacted using the announcement emoji.")
async def setup_draft(interaction: discord.Interaction,
    draft_object: str
    ):
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