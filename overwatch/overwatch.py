from redbot.core import commands
import discord
import requests
import random


class Overwatch(commands.Cog):
    """Overwatch Related Commands"""

    @commands.group(autohelp=True, aliases=["overwatch"])
    async def ow(self, ctx):
        """Overwatch Commands"""
        pass

    @ow.command(alias="stats")
    async def profile(self, ctx, account: str, region: str):
        """OW Profile Stats - Account must include the ID. Ensure profile is public for full stats"""
        account = account.replace("#", "-")
        try:
            r = requests.get(
                f"https://ow-api.com/v1/stats/pc/{region}/{account}/profile")
            colour = discord.Color.from_hsv(random.random(), 1, 1)
            embed = discord.Embed(title="Overwatch Profile Information", colour=colour)
            embed.set_author(name=r.json()['name'], icon_url=r.json()['icon'])
            embed.set_thumbnail(url=r.json()['icon'])
            embed.add_field(name="Name:", value=r.json()['name'], inline=True)
            embed.add_field(name="Level:", value=r.json()['level'], inline=True)
            embed.add_field(name="Prestige:", value=r.json()['prestige'], inline=True)
            if not r.json()['private']:
                embed.add_field(name="Games Won:", value=r.json()['gamesWon'], inline=True)
            else:
                embed.set_footer(text="Please set your profile status to public for more stats.")
            await ctx.send(embed=embed)
        except:
            await ctx.send("Request failed, please ensure you're entering the details correctly.")

    @ow.command()
    async def hero(self, ctx, account: str, region: str, hero: str):
        """OW Hero Stats - Account must include the ID. Profile must be public"""
        account = account.replace("#", "-")
        try:
            r = requests.get(
                f"https://ow-api.com/v1/stats/pc/{region}/{account}/heroes/{hero}")
            if not r.json()['private']:
                colour = discord.Color.from_hsv(random.random(), 1, 1)
                embed = discord.Embed(title="Overwatch Profile Information", colour=colour)
                embed.set_author(name=r.json()['name'], icon_url=r.json()['icon'])
                embed.set_thumbnail(url=r.json()['icon'])
                embed.add_field(name="Name:", value=r.json()['name'], inline=True)
                embed.add_field(name="Level:", value=r.json()['level'], inline=True)
                embed.add_field(name="Prestige:", value=r.json()['prestige'], inline=True)
                embed.add_field(name="Total Games Won:", value=r.json()['gamesWon'], inline=True)
                embed.add_field(name="---", value="---", inline=False)
                embed.add_field(name="Hero:", value=hero.capitalize(), inline=True)
                embed.add_field(name=hero.capitalize() + " Playtime:",
                                value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)]['timePlayed'],
                                inline=True)
                embed.add_field(name="Games Won:",
                                value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)]['gamesWon'],
                                inline=True)
                embed.add_field(name="Elims Per Life",
                                value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)][
                                    'eliminationsPerLife'],
                                inline=True)
                embed.add_field(name="Weapon Accuracy",
                                value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)][
                                          'weaponAccuracy'] + "%",
                                inline=True)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Your profile is set to private, we were unable to retrieve your stats.")

        except:
            await ctx.send("Request failed, please ensure you're entering the details correctly.")

    @ow.command()
    async def heroes(self, ctx, account: str, region: str, platform: str, *heroes: str):
        """OW Multiple Hero Stats - Account must include the ID. Profile must be public"""
        account = account.replace("#", "-")
        heroes = ",".join(heroes)
        if platform != "psn" or platform != "xbl":
            platform = "pc"
        r = requests.get(
            f"https://ow-api.com/v1/stats/{platform}/{region}/{account}/heroes/{heroes}")
        try:
            if not r.json()['private']:
                colour = discord.Color.from_hsv(random.random(), 1, 1)
                embed = discord.Embed(title="Overwatch Profile Information", colour=colour)
                embed.set_author(name=r.json()['name'], icon_url=r.json()['icon'])
                embed.set_thumbnail(url=r.json()['icon'])
                embed.add_field(name="Name:", value=r.json()['name'], inline=True)
                embed.add_field(name="Level:", value=r.json()['level'], inline=True)
                embed.add_field(name="Prestige:", value=r.json()['prestige'], inline=True)
                embed.add_field(name="Total Games Won:", value=r.json()['gamesWon'], inline=True)
                await ctx.send(embed=embed)
                for hero in (r.json()['quickPlayStats']['topHeroes']):
                    embed = discord.Embed(title="{} Information".format(hero.capitalize()), colour=colour)
                    embed.set_author(name=r.json()['name'], icon_url=r.json()['icon'])
                    embed.set_thumbnail(url=r.json()['icon'])
                    embed.add_field(name="Hero:", value=hero.capitalize(), inline=True)
                    embed.add_field(name=hero.capitalize() + " Playtime:",
                                    value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)]['timePlayed'],
                                    inline=True)
                    embed.add_field(name=hero.capitalize() + " Games Won:",
                                    value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)]['gamesWon'],
                                    inline=True)
                    embed.add_field(name=hero.capitalize() + " Elims Per Life",
                                    value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)][
                                        'eliminationsPerLife'],
                                    inline=True)
                    embed.add_field(name=hero.capitalize() + " Weapon Accuracy",
                                    value=str(r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)][
                                                  'weaponAccuracy']) + "%",
                                    inline=True)
                    await ctx.send(embed=embed)

            else:
                await ctx.send("Your profile is set to private, we were unable to retrieve your stats.")
        except:
            await ctx.send("Unable to retrieve results, please ensure you're entering the command correctly")

    @ow.group()
    async def console(self, ctx):
        """OW Commands"""
        pass

    @console.command()
    async def heroes(self, ctx, console: str, account: str, *heroes: str):
        """OW Multiple Hero Stats - Account = PSN Name or Gamertag!. Profile must be public"""
        heroes = ",".join(heroes)
        r = requests.get(
            f"https://ow-api.com/v1/stats/{console}/{account}/heroes/{heroes}")
        try:
            if not r.json()['private']:
                colour = discord.Color.from_hsv(random.random(), 1, 1)
                embed = discord.Embed(title="Overwatch Profile Information", colour=colour)
                embed.set_author(name=r.json()['name'], icon_url=r.json()['icon'])
                embed.set_thumbnail(url=r.json()['icon'])
                embed.add_field(name="Name:", value=r.json()['name'], inline=True)
                embed.add_field(name="Level:", value=r.json()['level'], inline=True)
                embed.add_field(name="Prestige:", value=r.json()['prestige'], inline=True)
                embed.add_field(name="Total Games Won:", value=r.json()['gamesWon'], inline=True)
                await ctx.send(embed=embed)
                for hero in (r.json()['quickPlayStats']['topHeroes']):
                    embed = discord.Embed(title="{} Information".format(hero.capitalize()), colour=colour)
                    embed.set_author(name=r.json()['name'], icon_url=r.json()['icon'])
                    embed.set_thumbnail(url=r.json()['icon'])
                    embed.add_field(name="Hero:", value=hero.capitalize(), inline=True)
                    embed.add_field(name=hero.capitalize() + " Playtime:",
                                    value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)]['timePlayed'],
                                    inline=True)
                    embed.add_field(name=hero.capitalize() + " Games Won:",
                                    value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)]['gamesWon'],
                                    inline=True)
                    embed.add_field(name=hero.capitalize() + " Elims Per Life",
                                    value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)][
                                        'eliminationsPerLife'],
                                    inline=True)
                    embed.add_field(name=hero.capitalize() + " Weapon Accuracy",
                                    value=str(r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)][
                                                  'weaponAccuracy']) + "%",
                                    inline=True)
                    await ctx.send(embed=embed)

            else:
                await ctx.send("Your profile is set to private, we were unable to retrieve your stats.")
        except:
            await ctx.send("Unable to retrieve results, please ensure you're entering the command correctly")

    @console.command()
    async def hero(self, ctx, console: str, account: str, hero: str):
        """OW Hero Stats - Account = PSN Name or Gamertag!. Profile must be public"""
        try:
            r = requests.get(
                f"https://ow-api.com/v1/stats/{console}/{account}/heroes/{hero}")
            if not r.json()['private']:
                colour = discord.Color.from_hsv(random.random(), 1, 1)
                embed = discord.Embed(title="Overwatch Profile Information", colour=colour)
                embed.set_author(name=r.json()['name'], icon_url=r.json()['icon'])
                embed.set_thumbnail(url=r.json()['icon'])
                embed.add_field(name="Name:", value=r.json()['name'], inline=True)
                embed.add_field(name="Level:", value=r.json()['level'], inline=True)
                embed.add_field(name="Prestige:", value=r.json()['prestige'], inline=True)
                embed.add_field(name="Total Games Won:", value=r.json()['gamesWon'], inline=True)
                embed.add_field(name="---", value="---", inline=False)
                embed.add_field(name="Hero:", value=hero.capitalize(), inline=True)
                embed.add_field(name=hero.capitalize() + " Playtime:",
                                value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)]['timePlayed'],
                                inline=True)
                embed.add_field(name="Games Won:",
                                value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)]['gamesWon'],
                                inline=True)
                embed.add_field(name="Elims Per Life",
                                value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)][
                                    'eliminationsPerLife'],
                                inline=True)
                embed.add_field(name="Weapon Accuracy",
                                value=r.json()['quickPlayStats']['topHeroes']['{}'.format(hero)][
                                          'weaponAccuracy'] + "%",
                                inline=True)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Your profile is set to private, we were unable to retrieve your stats.")

        except:
            await ctx.send("Request failed, please ensure you're entering the details correctly.")

    @console.command(alias="stats")
    async def profile(self, ctx, console: str, account: str):
        """OW Profile Stats - Account must be your PSN or Gamertag. Ensure profile is public for full stats"""
        try:
            r = requests.get(
                f"https://ow-api.com/v1/stats/{console}/{account}/profile")
            colour = discord.Color.from_hsv(random.random(), 1, 1)
            embed = discord.Embed(title="Overwatch Profile Information", colour=colour)
            embed.set_author(name=r.json()['name'], icon_url=r.json()['icon'])
            embed.set_thumbnail(url=r.json()['icon'])
            embed.add_field(name="Name:", value=r.json()['name'], inline=True)
            embed.add_field(name="Level:", value=r.json()['level'], inline=True)
            embed.add_field(name="Prestige:", value=r.json()['prestige'], inline=True)
            if not r.json()['private']:
                embed.add_field(name="Games Won:", value=r.json()['gamesWon'], inline=True)
            else:
                embed.set_footer(text="Please set your profile status to public for more stats.")
            await ctx.send(embed=embed)
        except:
            await ctx.send("Request failed, please ensure you're entering the details correctly.")
