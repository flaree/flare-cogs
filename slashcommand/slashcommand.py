import random

import discord
from discord.ext import commands
from discord_slash import SlashContext, cog_ext
from discord_slash.utils.manage_commands import create_choice, create_option


class SlashCommand(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(name="numbergame",
          description="play a simpe number game",
          options=[
            create_option(
              name="number",
              description="Pick a number",
              option_type=4,
              required=True,
            )]
            )

    async def numbergame(self, ctx, number: int):
        numberGuess = random.randint(1, 11)
        if number = numberGuess:
            await ctx.send("You Guessed The Correct Number!")
        else:
            await ctx.send("You Guessed The Wrong Number", hidden=True) # Send A Hidden Responce
