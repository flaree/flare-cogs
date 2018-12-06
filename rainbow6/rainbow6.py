from redbot.core import commands
import discord
import requests
import random


class Rainbow6(commands.Cog):
    """Rainbow6 Related Commands"""

    @commands.group(autohelp=True)
    async def r6(self, ctx):
        """R6 Commands"""
        pass

    @r6.command()
    async def profile(self, ctx, account: str, *platform: str):
        """R6 Profile Stats for Season 12"""
        platform = "".join(platform)
        if platform == "psn" or platform == "xbl":
            r = requests.post(
                "https://flareee.com/r6/getUser.php?name={}&platform={}&appcode=flare".format(account, platform))
            t = requests.post(
                "https://flareee.com/r6/getSmallUser.php?name={}&platform=uplay&appcode=flare".format(account,
                                                                                                      platform))
        else:
            r = requests.post(
                "https://flareee.com/r6/getUser.php?name={}&appcode=flare".format(account))
            t = requests.post(
                "https://flareee.com/r6/getSmallUser.php?name={}&platform=uplay&appcode=flare".format(account))
        p = (r.json()["players"]["{}".format(list(t.json().keys())[0])])
        colour = discord.Color.from_hsv(random.random(), 1, 1)
        embed = discord.Embed(title="R6 Profile for {}".format(account), colour=colour)
        embed.set_thumbnail(url=p['rankInfo']['image'])
        embed.add_field(name="Name:", value=p['nickname'], inline=True)
        embed.add_field(name="Rank:", value=p['rankInfo']['name'], inline=True)
        embed.add_field(name="Season:", value=p['season'], inline=True)
        embed.add_field(name="Games Won:", value=p['wins'], inline=True)
        embed.add_field(name="Games Lost:", value=p['losses'], inline=True)
        embed.add_field(name="Abandons:", value=p['abandons'], inline=True)
        embed.add_field(name="MMR:", value=round(p['mmr']), inline=True)
        await ctx.send(embed=embed)

    @r6.command()
    async def season(self, ctx, account: str, season: int, platform=None):
        """R6 Profile Stats for a custom season"""
        if 0 > season or season > 12:
            season = 12
        if platform == "psn" or platform == "xbl":
            r = requests.post(
                f"https://flareee.com/r6/getUser.php?name={account}&platform={platform}&appcode=flare&season={season}")
            t = requests.post(
                f"https://flareee.com/r6/getSmallUser.php?name={account}&platform={platform}&appcode=flare")
        else:
            r = requests.post(
                f"https://flareee.com/r6/getUser.php?name={account}&appcode=flare&season={season}")
            t = requests.post(
                f"https://flareee.com/r6/getSmallUser.php?name={account}&appcode=flare")
        p = (r.json()["players"]["{}".format(list(t.json().keys())[0])])
        colour = discord.Color.from_hsv(random.random(), 1, 1)
        embed = discord.Embed(title="R6 Profile for {}".format(account), colour=colour)
        embed.set_thumbnail(url=p['rankInfo']['image'])
        embed.add_field(name="Name:", value=p['nickname'], inline=True)
        embed.add_field(name="Rank:", value=p['rankInfo']['name'], inline=True)
        embed.add_field(name="Season:", value=p['season'], inline=True)
        embed.add_field(name="Games Won:", value=p['wins'], inline=True)
        embed.add_field(name="Games Lost:", value=p['losses'], inline=True)
        embed.add_field(name="Abandons:", value=p['abandons'], inline=True)
        embed.add_field(name="MMR:", value=round(p['mmr']), inline=True)
        await ctx.send(embed=embed)

    @r6.command()
    async def operator(self, ctx, operator: str, account: str, platform=None):
        """R6 Profile Stats for a certain Operator"""
        if platform == "psn" or platform == "xbl":
            r = requests.post(
                "https://flareee.com/r6/getOperators.php?name={}&platform={}&appcode=flare".format(account, platform))
            t = requests.post(
                "https://flareee.com/r6/getSmallUser.php?name={}&platform={}&appcode=flare".format(account, platform))
        else:
            r = requests.post(
                "https://flareee.com/r6/getOperators.php?name={}&appcode=flare".format(account))
            t = requests.post(
                "https://flareee.com/r6/getSmallUser.php?name={}&appcode=flare".format(account))
        p = (r.json()["players"]["{}".format(list(t.json().keys())[0])]["{}".format(operator)])
        colour = discord.Color.from_hsv(random.random(), 1, 1)
        embed = discord.Embed(title="Operator Information for {}".format(ctx.author), colour=colour)
        embed.add_field(name="Operator:", value=operator.capitalize(), inline=True)
        embed.add_field(name="Rounds Won:", value=p['operatorpvp_roundwon'], inline=True)
        embed.add_field(name="Rounds Lost:", value=p['operatorpvp_roundlost'], inline=True)
        embed.add_field(name="Kills:", value=p['operatorpvp_kills'], inline=True)
        embed.add_field(name="Deaths:", value=p['operatorpvp_death'], inline=True)
        embed.add_field(name="Time Played:", value=round(int(p['operatorpvp_timeplayed']) / 60), inline=True)
        await ctx.send(embed=embed)

    @r6.command()
    async def listoperators(self, ctx):
        """List all R6 Operators"""
        r = requests.post("https://flareee.com/r6/getOperators.php?name=flareee&platform=uplay&appcode=flare")
        colour = discord.Color.from_hsv(random.random(), 1, 1)
        my_too_long_string = (r.json()["players"]["5702e49a-7e4d-4a2a-80e5-50b2bfabfcf9"])
        embed = discord.Embed(title="Operators Information for {}".format(ctx.author), colour=colour)
        for operators in my_too_long_string:
            embed.add_field(name=str(operators).capitalize(), value="-", inline=True)
        await ctx.send(embed=embed)
