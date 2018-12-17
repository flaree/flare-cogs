import random
import discord
import requests
from redbot.core import commands, Config
from .operators import ops

defaults = {"Profiles": {},
            "Platform": {}}


class Rainbow6(commands.Cog):
    """Rainbow6 Related Commands"""

    def __init__(self):
        self.database = Config.get_conf(
            self, identifier=7258295620, force_registration=True)
        self.database.register_global(**defaults)

    @commands.group(autohelp=True)
    async def r6(self, ctx):
        """R6 Commands"""
        pass

    @r6.command()
    async def setprofile(self, ctx, account: str, platforms=None):
        """Set profile for automatic lookup via r6 profile"""
        if platforms != "psn" or platforms != "xbl":
            platforms = "uplay"
        async with self.database.Profiles() as profiles:
            key1 = ctx.author
            profiles[key1] = account
        async with self.database.Platform() as platform:
            key1 = ctx.author
            platform[key1] = platforms
        await ctx.send(f"Profile and platform updated successfully.")

    @r6.command()
    async def profile(self, ctx, member: discord.Member = None):
        """R6 Profile Stats for your set account. """
        data = await self.database.all()
        if member is None:
            member = ctx.author
        try:
            r = requests.get(
                "https://flareee.com/r6/getUser.php?name={}&platform={}&appcode=flare".format(
                    data['Profiles']['{}'.format(member)], data['Platform']['{}'.format(member)]))
            t = requests.get(
                "https://flareee.com/r6/getSmallUser.php?name={}&platform=uplay&appcode=flare".format(
                    data['Profiles']['{}'.format(member)], data['Platform']['{}'.format(member)]))
            p = (r.json()["players"]["{}".format(list(t.json().keys())[0])])
            colour = discord.Color.from_hsv(random.random(), 1, 1)
            embed = discord.Embed(title="R6 Profile for {}".format(data['Profiles']['{}'.format(member)]),
                                  colour=colour)
            embed.set_thumbnail(url=p['rankInfo']['image'])
            embed.add_field(name="Name:", value=p['nickname'], inline=True)
            embed.add_field(
                name="Rank:", value=p['rankInfo']['name'], inline=True)
            embed.add_field(name="Season:", value=p['season'], inline=True)
            embed.add_field(name="Level:", value=p['level'], inline=True)
            embed.add_field(name="Games Won:", value=p['wins'], inline=True)
            embed.add_field(name="Games Lost:", value=p['losses'], inline=True)
            embed.add_field(name="Abandons:", value=p['abandons'], inline=True)
            embed.add_field(name="MMR:", value=round(p['mmr']), inline=True)
            await ctx.send(embed=embed)
        except KeyError:
            await ctx.send("Ensure you've set your profile via [p]r6 setprofile. (Replace [p] with the bot prefix.")

    @r6.command()
    async def lookup(self, ctx, account: str, platform=None):
        """R6 Profile Stats for Season 12 - Platform defaults to uplay. Other choices: "xbl" and "psn" """
        if platform != "psn" or platform != "xbl":
            platform = "uplay"
        try:
            r = requests.get(
                "https://flareee.com/r6/getUser.php?name={}&platform={}&appcode=flare".format(account, platform))
            t = requests.get(
                "https://flareee.com/r6/getSmallUser.php?name={}&platform=uplay&appcode=flare".format(account,
                                                                                                      platform))
            p = (r.json()["players"]["{}".format(list(t.json().keys())[0])])
            colour = discord.Color.from_hsv(random.random(), 1, 1)
            embed = discord.Embed(
                title="R6 Profile for {}".format(account), colour=colour)
            embed.set_thumbnail(url=p['rankInfo']['image'])
            embed.add_field(name="Name:", value=p['nickname'], inline=True)
            embed.add_field(
                name="Rank:", value=p['rankInfo']['name'], inline=True)
            embed.add_field(name="Season:", value=p['season'], inline=True)
            embed.add_field(name="Level:", value=p['level'], inline=True)
            embed.add_field(name="Games Won:", value=p['wins'], inline=True)
            embed.add_field(name="Games Lost:", value=p['losses'], inline=True)
            embed.add_field(name="Abandons:", value=p['abandons'], inline=True)
            embed.add_field(name="MMR:", value=round(p['mmr']), inline=True)
            await ctx.send(embed=embed)
        except:
            await ctx.send('Failed, ensure your name and platform are both valid. Check the help for more info.')

    @r6.command()
    async def season(self, ctx, account: str, season: int, platform=None):
        """R6 Profile Stats for a custom season - Platform defaults to uplay. Other choices: "xbl" and "psn" """
        if 0 > season or season > 12:
            season = 12
        if platform != "psn" or platform != "xbl":
            platform = "uplay"
        try:
            r = requests.get(
                f"https://flareee.com/r6/getUser.php?name={account}&platform={platform}&appcode=flare&season={season}")
            t = requests.get(
                f"https://flareee.com/r6/getSmallUser.php?name={account}&platform={platform}&appcode=flare")
            p = (r.json()["players"]["{}".format(list(t.json().keys())[0])])
            colour = discord.Color.from_hsv(random.random(), 1, 1)
            embed = discord.Embed(
                title="R6 Profile for {}".format(account), colour=colour)
            embed.set_thumbnail(url=p['rankInfo']['image'])
            embed.add_field(name="Name:", value=p['nickname'], inline=True)
            embed.add_field(
                name="Rank:", value=p['rankInfo']['name'], inline=True)
            embed.add_field(name="Season:", value=p['season'], inline=True)
            embed.add_field(name="Games Won:", value=p['wins'], inline=True)
            embed.add_field(name="Games Lost:", value=p['losses'], inline=True)
            embed.add_field(name="Abandons:", value=p['abandons'], inline=True)
            embed.add_field(name="MMR:", value=round(p['mmr']), inline=True)
            await ctx.send(embed=embed)
        except:
            await ctx.send(
                'Failed, ensure your name, season number and platform are valid. Check the help for more info.')

    @r6.command()
    async def operator(self, ctx, account: str, operator: str, platform=None):
        """R6 Profile Stats for a certain Operator - Platform defaults to uplay. Other choices: "xbl" and "psn" """
        if platform != "psn" or platform != "xbl":
            platform = "uplay"
        try:
            r = requests.get(
                "https://flareee.com/r6/getOperators.php?name={}&platform={}&appcode=flare".format(account,
                                                                                                   platform))
            t = requests.get(
                "https://flareee.com/r6/getSmallUser.php?name={}&platform={}&appcode=flare".format(account,
                                                                                                   platform))
            p = (r.json()["players"]["{}".format(
                list(t.json().keys())[0])]["{}".format(operator)])
            colour = discord.Color.from_hsv(random.random(), 1, 1)
            embed = discord.Embed(
                title="Operator Information for {}".format(ctx.author), colour=colour)
            embed.add_field(name="Operator:",
                            value=operator.capitalize(), inline=True)
            embed.add_field(name="Rounds Won:",
                            value=p['operatorpvp_roundwon'], inline=True)
            embed.add_field(name="Rounds Lost:",
                            value=p['operatorpvp_roundlost'], inline=True)
            embed.add_field(
                name="Kills:", value=p['operatorpvp_kills'], inline=True)
            embed.add_field(
                name="Deaths:", value=p['operatorpvp_death'], inline=True)
            embed.add_field(name="Time Played:", value=round(
                int(p['operatorpvp_timeplayed']) / 60), inline=True)
            await ctx.send(embed=embed)
        except:
            await ctx.send(
                'Failed, ensure your name, platform & operator name are valid. Check the help for more info.')

    @r6.command()
    async def operators(self, ctx, account: str, stats: str, platform=None):
        """R6 Profile Stats for all operators - Stats can be kills, roundwon or timeplayed,Platform defaults to uplay. Other choices: "xbl" and "psn" """
        if platform != "psn" or platform != "xbl":
            platform = "uplay"

        r = requests.get(
            "https://flareee.com/r6/getOperators.php?name={}&platform={}&appcode=flare".format(account,
                                                                                               platform))
        t = requests.get(
            "https://flareee.com/r6/getSmallUser.php?name={}&platform={}&appcode=flare".format(account,
                                                                                               platform))
        q = r.json()["players"]["{}".format(list(t.json().keys())[0])]
        colour = discord.Color.from_hsv(random.random(), 1, 1)
        embed = discord.Embed(
            title="Operator Information for {}/{}".format(account, ctx.author), colour=colour)
        emb = discord.Embed(
            title="Operator Information for {}/{}".format(account, ctx.author), colour=colour)
        i = 0
        while i < len(ops):
            if i < 21:
                if stats == "timeplayed":
                    embed.add_field(name="{} {}:".format(ops[i].capitalize(), stats.capitalize()),
                                    value=round(
                                        int(q["{}".format(ops[i])]['operatorpvp_{}'.format(stats)]) / 60),
                                    inline=True)
                else:
                    embed.add_field(name="{} {}:".format(ops[i].capitalize(), stats.capitalize()),
                                    value=q["{}".format(ops[i])]['operatorpvp_{}'.format(stats)], inline=True)
            else:
                if stats == "timeplayed":
                    emb.add_field(name="{} {}:".format(ops[i].capitalize(), stats.capitalize()),
                                  value=round(
                                      int(q["{}".format(ops[i])]['operatorpvp_{}'.format(stats)]) / 60),
                                  inline=True)
                else:
                    emb.add_field(name="{} {}:".format(ops[i].capitalize(), stats.capitalize()),
                                  value=q["{}".format(ops[i])]['operatorpvp_{}'.format(stats)], inline=True)
            i += 1
        await ctx.send(embed=embed)
        await ctx.send(embed=emb)
