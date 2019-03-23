from redbot.core import commands
import discord
import requests
import random


class Csgo(commands.Cog):
    """CS:GO Related Commands"""

    @commands.command(aliases=["csgo", "skins", "csgoskins"])
    async def skin(self, ctx, currency: str, *skin: str):
        """CSGO Skin/Item Lookup.- Very specific EX: [p]skin USD/EUR/GBP M4A1-S | Cyrex (Factory New)  *NOTE*: Will not work with Stat Trak items!"""
        message = ctx.message
        s = "%20".join(skin).title()
        c = currency.upper()
        try:
            r = requests.get(
                "https://csgobackpack.net/api/GetItemPrice/?currency={}&id={}&time=7&icon=1".format(
                    c, s
                )
            )
            if c == "USD":
                curr = "$"
            elif c == "EUR":
                curr = "€"
            elif c == "GBP":
                curr = "£"
            # Random Hex Value for embed colour.
            colour = discord.Color.from_hsv(random.random(), 1, 1)
            if r.json()["success"] == True:
                embed = discord.Embed(title="CS:GO Skin Information", colour=colour)
                embed.set_thumbnail(url=r.json()["icon"])
                embed.add_field(name="Skin/Item", value=" ".join(skin).title(), inline=False)
                embed.add_field(
                    name="Lowest Price:", value=curr + r.json()["lowest_price"], inline=True
                )
                embed.add_field(
                    name="Average Price:", value=curr + r.json()["average_price"], inline=True
                )
                embed.add_field(
                    name="Highest Price:", value=curr + r.json()["highest_price"], inline=True
                )
                embed.add_field(
                    name="Median Price:", value=curr + r.json()["median_price"], inline=True
                )
                await ctx.send(embed=embed)
                await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
            else:
                await ctx.send(
                    "There was an error processing your request, ensure you're formatting it correctly."
                )
        except ValueError:
            await ctx.send(
                "Failed, ensure that the currency and skin are both valid. Check the help for more info."
            )
