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

#imports discord token from an encrypted .env file
import os
from dotenv import load_dotenv

#load variables from .env file
load_dotenv()  
TOKEN = os.getenv("DISCORD_TOKEN")


#discord imports
import discord
from discord.ext import commands

#setup intents (just message_content isn't needed for slash commands, but safe to keep)
intents = discord.Intents.default()
intents.message_content = True

#assigns "!" as the command prefix for all commands
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

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
    -test command (says hello to the user prompting the command)
"""

#test command
@bot.tree.command(name="hello", description="Say hello to the bot!")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello, {interaction.user.display_name}!")

"""
ADMIN COMMANDS
    -create_draft (creates the draft, and its dedicated directory)
"""

#command that creates the draft
@bot.tree.command(name="create_draft", description="Creates the Draft")
async def create_draft(interaction: discord.Interaction):
    await interaction.response.send_message(f"Command Not Yet Implemented",ephemeral=True)

"""
USER COMMANDS
    -pick (reserves a single pick for the next turn)
    -reserve_picks (reserves multiple picks so the bot can automatically pick from it)
    -clear_pick (clears the picks from the user)
"""

#command that lets the user pick one bot
    #1 mandatory parameter for team pick
@bot.tree.command(name="pick", description="Reserve a Single Pick for your next turn")
async def pick(interaction: discord.Interaction):
    await interaction.response.send_message(f"Command Not Yet Implemented",ephemeral=True)

#command that lets the user reserve multiple picks (up to 4) so the bot can automatically pick for them
    #1 mandatory parameter for double picking teams
    #1 mandatory parameter for team pick
    #3 optional team pick parameters
@bot.tree.command(name="reserve_picks", description="Lets you select a multitude of teams for the bot to automaticly pick for you")
async def create_draft(interaction: discord.Interaction):
    await interaction.response.send_message(f"Command Not Yet Implemented",ephemeral=True)

#command that lets the user clear their list of picks
@bot.tree.command(name="clear_pick", description="Clears any picks that you currently have.")
async def create_draft(interaction: discord.Interaction):
    await interaction.response.send_message(f"Command Not Yet Implemented",ephemeral=True)

#runs the bot on the token
bot.run(TOKEN)