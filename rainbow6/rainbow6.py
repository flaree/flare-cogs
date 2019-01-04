import random
import discord
import requests
from redbot.core import commands, Config, checks
from .operators import ops
from PIL import Image, ImageDraw, ImageFont

defaults = {"Profiles": {},
            "Platform": {},
            "Picture": ["True"]}


class Rainbow6(commands.Cog):
    """Rainbow6 Related Commands"""

    def __init__(self):
        self.database = Config.get_conf(
            self, identifier=7258295620, force_registration=True)
        self.database.register_global(**defaults)

    def round_corner(self, radius):
        """Draw a round corner"""
        corner = Image.new('L', (radius, radius), 0)
        draw = ImageDraw.Draw(corner)
        draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=255)
        return corner

    def add_corners(self, im, rad):
        # https://stackoverflow.com/questions/7787375/python-imaging-library-pil-drawing-rounded-rectangle-with-gradient
        width, height = im.size
        alpha = Image.new('L', im.size, 255)
        origCorner = self.round_corner(rad)
        corner = origCorner
        alpha.paste(corner, (0, 0))
        corner = origCorner.rotate(90)
        alpha.paste(corner, (0, height - rad))
        corner = origCorner.rotate(180)
        alpha.paste(corner, (width - rad, height - rad))
        corner = origCorner.rotate(270)
        alpha.paste(corner, (width - rad, 0))
        im.putalpha(alpha)
        return im

    @commands.group(autohelp=True)
    async def r6(self, ctx):
        """R6 Commands"""
        pass

    @r6.command()
    @checks.admin_or_permissions(administrator=True)
    async def picture(self, ctx, type: str):
        """Set picture/embed lookup"""
        if type == "True":
            async with self.database.Picture() as picture:
                picture[0] = "True"
            await ctx.send("The bot will now send pictures instead of embeds.")
        elif type == "False":
            async with self.database.Picture() as picture:
                picture[0] = "False"
            await ctx.send("The bot will now send embeds instead of pictures.")
        else:
            await ctx.send(f"Valid choices are True of False.")

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
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
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
            s = requests.get("https://flareee.com/r6/getStats.php?name={}&platform=uplay&appcode=flare".format(
                data['Profiles']['{}'.format(member)]))
            p = (r.json()["players"]["{}".format(list(t.json().keys())[0])])
            q = (s.json()["players"]["{}".format(list(t.json().keys())[0])])
            if data["Picture"][0] == "True":
                img = Image.new("RGBA", (340, 560), (17, 17, 17, 0))
                aviholder = self.add_corners(Image.new("RGBA", (140, 140), (255, 255, 255, 255)), 10)
                nameplate = self.add_corners(Image.new("RGBA", (180, 90), (0, 0, 0, 255)), 10)
                img.paste(nameplate, (155, 10), nameplate)
                img.paste(aviholder, (10, 10), aviholder)
                url = p['rankInfo']['image']
                im = Image.open(requests.get(url, stream=True).raw)
                im_size = 130, 130
                im.thumbnail(im_size)
                img.paste(im, (14, 15))
                draw = ImageDraw.Draw(img)
                font2 = ImageFont.truetype(
                    "/home/flare/.loca./share/R6-Stats-Red/cogs/CogManager/cogs/rainbow6/ARIALUNI.ttf",
                    22)
                font = ImageFont.truetype(
                    "/home/flare/.loca./share/R6-Stats-Red/cogs/CogManager/cogs/rainbow6/ARIALUNI.ttf",
                    24)
                draw.text((162, 14), f"{data['Profiles']['{}'.format(member)]}", fill=(255, 255, 255, 255), font=font)
                draw.text((10, 180), "Rank: {}".format(p['rankInfo']['name']), fill=(255, 255, 255, 255), font=font)
                draw.text((162, 40), "Level: {}".format(p['level']), fill=(255, 255, 255, 255), font=font)
                draw.text((162, 70), "Season 12 Stats", fill=(255, 255, 255, 255), font=font2)
                draw.text((10, 220), "Wins: {}".format(p['wins']), fill=(255, 255, 255, 255), font=font)
                draw.text((10, 260), "Losses: {}".format(p['losses']), fill=(255, 255, 255, 255), font=font)
                draw.text((10, 300), "MMR: {}".format(round(p['mmr'])), fill=(255, 255, 255, 255), font=font)
                draw.text((10, 340), "Abandons: {}".format(p['abandons']), fill=(255, 255, 255, 255), font=font)
                draw.text((10, 380), "Ranked Kills: {}".format(q['rankedpvp_kills']), fill=(255, 255, 255, 255),
                          font=font)
                draw.text((10, 420), "Ranked Deaths: {}".format(q['rankedpvp_death']), fill=(255, 255, 255, 255),
                          font=font)
                kdr = (int(q['rankedpvp_kills']) / int(q['rankedpvp_death']))
                draw.text((10, 460), "Ranked KDR: {}".format(round(kdr, 2)), fill=(255, 255, 255, 255), font=font)
                wlr = (int(p['wins']) / (int(p['wins']) + int(p['losses']))) * 100
                draw.text((10, 500), "Ranked W/LR: {}".format(round(wlr, 2)), fill=(255, 255, 255, 255), font=font)

                img.save("/home/flare/.loca./share/R6-Stats-Red/cogs/CogManager/cogs/rainbow6/r6.png")
                image = discord.File("/home/flare/.loca./share/R6-Stats-Red/cogs/CogManager/cogs/rainbow6/r6.png")
                await ctx.send(file=image)
            else:
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
                embed.add_field(name="Casual Kills:", value=q['casualpvp_kills'], inline=True)
                embed.add_field(name="Casual Deaths:", value=q['casualpvp_death'], inline=True)
                await ctx.send(embed=embed)
        except KeyError:
            await ctx.send("Ensure you've set your profile via [p]r6 setprofile. (Replace [p] with the bot prefix.)")

    @commands.command()
    async def accinfo(self, ctx, member: discord.Member = None):
        """Account Info"""
        data = await self.database.all()
        if member is None:
            member = ctx.author
        try:
            profile = data['Profiles']['{}'.format(member)]
            platform = data['Platform']['{}'.format(member)]
            await ctx.send(f"Profile Name: {profile}")
            await ctx.send(f"Platform: {platform}")
        except KeyError:
            await ctx.send("You do not have an account set, please set one via .r6 setprofile")

    @r6.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    async def lookup(self, ctx, account: str, platform=None):
        """R6 Profile Stats for Season 12 - Platform defaults to uplay. Other choices: "xbl" and "psn" """
        data = await self.database.all()
        if platform != "psn" or platform != "xbl":
            platform = "uplay"
        try:
            r = requests.get(
                "https://flareee.com/r6/getUser.php?name={}&platform={}&appcode=flare".format(account, platform))
            t = requests.get(
                "https://flareee.com/r6/getSmallUser.php?name={}&platform=uplay&appcode=flare".format(account))
            s = requests.get(
                "https://flareee.com/r6/getStats.php?name={}&platform={}&appcode=flare".format(account, platform))
            p = (r.json()["players"]["{}".format(list(t.json().keys())[0])])
            q = (s.json()["players"]["{}".format(list(t.json().keys())[0])])
            if data["Picture"][0] == "True":
                img = Image.new("RGBA", (340, 520), (17, 17, 17, 0))
                aviholder = self.add_corners(Image.new("RGBA", (140, 140), (255, 255, 255, 255)), 10)
                nameplate = self.add_corners(Image.new("RGBA", (180, 90), (0, 0, 0, 255)), 10)
                img.paste(nameplate, (155, 10), nameplate)
                img.paste(aviholder, (10, 10), aviholder)
                url = p['rankInfo']['image']
                im = Image.open(requests.get(url, stream=True).raw)
                im_size = 130, 130
                im.thumbnail(im_size)
                img.paste(im, (14, 15))
                draw = ImageDraw.Draw(img)
                font2 = ImageFont.truetype(
                    "/home/flare/.loca./share/R6-Stats-Red/cogs/CogManager/cogs/rainbow6/ARIALUNI.ttf",
                    22)
                font = ImageFont.truetype(
                    "/home/flare/.loca./share/R6-Stats-Red/cogs/CogManager/cogs/rainbow6/ARIALUNI.ttf",
                    24)
                draw.text((162, 14), f"{account}", fill=(255, 255, 255, 255), font=font)
                draw.text((10, 180), "Rank: {}".format(p['rankInfo']['name']), fill=(255, 255, 255, 255), font=font)
                draw.text((162, 40), "Level: {}".format(p['level']), fill=(255, 255, 255, 255), font=font)
                draw.text((162, 70), f"Season 12 Stats", fill=(255, 255, 255, 255), font=font2)
                draw.text((10, 220), "Wins: {}".format(p['wins']), fill=(255, 255, 255, 255), font=font)
                draw.text((10, 260), "Losses: {}".format(p['losses']), fill=(255, 255, 255, 255), font=font)
                draw.text((10, 300), "MMR: {}".format(round(p['mmr'])), fill=(255, 255, 255, 255), font=font)
                draw.text((10, 340), "Abandons: {}".format(p['abandons']), fill=(255, 255, 255, 255), font=font)
                draw.text((10, 380), "Casual Kills: {}".format(q['casualpvp_kills']), fill=(255, 255, 255, 255),
                          font=font)
                draw.text((10, 420), "Casual Deaths: {}".format(q['casualpvp_death']), fill=(255, 255, 255, 255),
                          font=font)
                kdr = (int(q['casualpvp_kills']) / int(q['casualpvp_death']))
                draw.text((10, 460), "Casual KDR: {}".format(round(kdr, 2)), fill=(255, 255, 255, 255), font=font)

                img.save("/home/flare/.loca./share/R6-Stats-Red/cogs/CogManager/cogs/rainbow6/r6.png")
                image = discord.File("/home/flare/.loca./share/R6-Stats-Red/cogs/CogManager/cogs/rainbow6/r6.png")
                await ctx.send(file=image)
            else:
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
                embed.add_field(name="Casual Kills:", value=q['casualpvp_kills'], inline=True)
                embed.add_field(name="Casual Deaths:", value=q['casualpvp_death'], inline=True)
                await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(e)

    @r6.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.guild)
    async def season(self, ctx, account: str, season: int, platform=None):
        """R6 Profile Stats for a custom season - Platform defaults to uplay. Other choices: "xbl" and "psn" """
        data = await self.database.all()
        if 0 > season or season > 12:
            season = 12
        if platform != "psn" or platform != "xbl":
            platform = "uplay"
        try:
            r = requests.get(
                f"https://flareee.com/r6/getUser.php?name={account}&platform={platform}&appcode=flare&season={season}")
            t = requests.get(
                f"https://flareee.com/r6/getSmallUser.php?name={account}&platform={platform}&appcode=flare")

            s = requests.get("https://flareee.com/r6/getStats.php?name={}&platform={}&appcode=flare".format(account,
                                                                                                            platform))
            p = (r.json()["players"]["{}".format(list(t.json().keys())[0])])
            q = (s.json()["players"]["{}".format(list(t.json().keys())[0])])
            if data["Picture"][0] == "True":
                img = Image.new("RGBA", (340, 520), (17, 17, 17, 0))
                aviholder = self.add_corners(Image.new("RGBA", (140, 140), (255, 255, 255, 255)), 10)
                nameplate = self.add_corners(Image.new("RGBA", (180, 90), (0, 0, 0, 255)), 10)
                img.paste(nameplate, (155, 10), nameplate)
                img.paste(aviholder, (10, 10), aviholder)
                url = p['rankInfo']['image']
                im = Image.open(requests.get(url, stream=True).raw)
                im_size = 130, 130
                im.thumbnail(im_size)
                img.paste(im, (14, 15))
                draw = ImageDraw.Draw(img)
                font2 = ImageFont.truetype(
                    "/home/flare/.loca./share/R6-Stats-Red/cogs/CogManager/cogs/rainbow6/ARIALUNI.ttf",
                    22)
                font = ImageFont.truetype(
                    "/home/flare/.loca./share/R6-Stats-Red/cogs/CogManager/cogs/rainbow6/ARIALUNI.ttf",
                    24)
                draw.text((162, 14), f"{account}", fill=(255, 255, 255, 255), font=font)
                draw.text((10, 180), "Rank: {}".format(p['rankInfo']['name']), fill=(255, 255, 255, 255), font=font)
                draw.text((162, 40), "Level: {}".format(p['level']), fill=(255, 255, 255, 255), font=font)
                draw.text((162, 70), f"Season {season} Stats", fill=(255, 255, 255, 255), font=font2)
                draw.text((10, 220), "Wins: {}".format(p['wins']), fill=(255, 255, 255, 255), font=font)
                draw.text((10, 260), "Losses: {}".format(p['losses']), fill=(255, 255, 255, 255), font=font)
                draw.text((10, 300), "MMR: {}".format(round(p['mmr'])), fill=(255, 255, 255, 255), font=font)
                draw.text((10, 340), "Abandons: {}".format(p['abandons']), fill=(255, 255, 255, 255), font=font)
                draw.text((10, 380), "Casual Kills: {}".format(q['casualpvp_kills']), fill=(255, 255, 255, 255),
                          font=font)
                draw.text((10, 420), "Casual Deaths: {}".format(q['casualpvp_death']), fill=(255, 255, 255, 255),
                          font=font)
                kdr = (int(q['casualpvp_kills']) / int(q['casualpvp_death']))
                draw.text((10, 460), "Casual KDR: {}".format(round(kdr, 2)), fill=(255, 255, 255, 255), font=font)

                img.save("/home/flare/.loca./share/R6-Stats-Red/cogs/CogManager/cogs/rainbow6/r6.png")
                image = discord.File("/home/flare/.loca./share/R6-Stats-Red/cogs/CogManager/cogs/rainbow6/r6.png")
                await ctx.send(file=image)
            else:
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
                embed.add_field(name="Casual Kills:", value=q['casualpvp_kills'], inline=True)
                embed.add_field(name="Casual Deaths:", value=q['casualpvp_death'], inline=True)
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
                                        int(q["{}".format(ops[i])]['operatorpvp_{}'.format(stats)]) / 3600),
                                    inline=True)
                else:
                    embed.add_field(name="{} {}:".format(ops[i].capitalize(), stats.capitalize()),
                                    value=q["{}".format(ops[i])]['operatorpvp_{}'.format(stats)], inline=True)
            else:
                if stats == "timeplayed":
                    emb.add_field(name="{} {}:".format(ops[i].capitalize(), stats.capitalize()),
                                  value=round(
                                      int(q["{}".format(ops[i])]['operatorpvp_{}'.format(stats)]) / 3600),
                                  inline=True)
                else:
                    emb.add_field(name="{} {}:".format(ops[i].capitalize(), stats.capitalize()),
                                  value=q["{}".format(ops[i])]['operatorpvp_{}'.format(stats)], inline=True)
            i += 1
        await ctx.send(embed=embed)
        await ctx.send(embed=emb)
