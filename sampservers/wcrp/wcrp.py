import discord
from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import pagify
from random import randint, choice
from samp_client.client import SampClient
import aiohttp
import asyncio
from prettytable import PrettyTable

BaseCog = getattr(commands, "Cog", object)


class Wcrp(BaseCog):
    """WC-RP's Commands"""

    def __init__(self, bot):
        self.bot = bot
        defaults_global = {"facs": {}}
        self.config = Config.get_conf(self, identifier=3523545667, force_registration=True)
        self.config.register_global(**defaults_global)
        self._session = aiohttp.ClientSession()

    async def __unload(self):
        asyncio.get_event_loop().create_task(self._session.close())

    async def get(self, url):
        async with self._session.get(url) as response:
            return await response.json()

    async def on_member_update(self, before, after):
        channel = self.bot.get_channel(537310109181673492)
        r = "https://api.samp-servers.net/v2/server/server.wc-rp.com:7777"
        req = await self.get(r)
        players = int(f"{req['core']['pc']}")
        if players < 10:
            u10 = str(channel.name[17:18])
        else:
            u10 = str(channel.name[17:19])
        if u10 != str(players):
            playerss = f"Current Players: {players}/400"
            await channel.edit(name=f"{playerss}")

    @commands.command(
        pass_context=True,
        aliases=["serverip", "ips", "wcrp", "wc-rp", "site", "website", "forum", "forums"],
    )
    async def ip(self, ctx):
        """WC-RP's server IP."""
        r = "https://api.samp-servers.net/v2/server/server.wc-rp.com:7777"
        req = await self.get(r)
        version = f"{req['core']['gm']}"
        samp = f"{req['core']['vn']}"
        colour = randint(0, 0xFFFFFF)
        embed = discord.Embed(
            title="West Coast Roleplay Information", colour=discord.Colour(value=colour)
        )
        embed.add_field(name="IP", value="server.wc-rp.com:7777", inline=True)
        embed.add_field(name="Numerical IP", value="63.251.20.189:7777", inline=True)
        embed.add_field(name="SA-MP Version", value=samp, inline=True)
        embed.add_field(name="Forums", value="https://wc-rp.com", inline=True)
        embed.add_field(
            name="Discord Invite Link", value="https://discord.gg/2jZYuZ7", inline=True
        )
        embed.add_field(name="Server Version", value=version, inline=True)
        embed.set_footer(text="WC-RP | 2008-19! ")
        await ctx.send(embed=embed)

    @commands.has_any_role(
        "Management",
        "Senior Administrator",
        "Server Owner",
        "server Manager",
        "Scripter",
        "Lead Administrator",
    )
    @commands.command()
    async def iplookup(self, ctx, ip: str):
        """IPLookup API"""
        ip1 = "http://api.ipstack.com/{}?access_key=6c5ddc76ac6b10405123ac249aff6bf8&format=1".format(
            ip
        )
        ip2 = "http://proxycheck.io/v2/{}?key=6n5t9m-353305-68f6j3-1qfw04&vpn=1&asn=1&node=1&time=1&inf=0&port=1&seen=1&days=7&tag=msg".format(
            ip
        )
        ip3 = "http://check.getipintel.net/check.php?ip={}&contact=flare2399@gmail.com&format=json&flags=m".format(
            ip
        )
        r = await self.get(ip1)
        s = await self.get(ip2)
        t = await self.get(ip3)
        user = ctx.author
        message = ctx.message
        colour = randint(0, 0xFFFFFF)  # Random Hex Value for embed colour.
        try:
            embed = discord.Embed(
                title=f"IP Lookup Information for {ip}",
                colour=discord.Colour(value=colour),
                timestamp=ctx.message.created_at,
            )
            embed.add_field(name="Country:", value=r["country_name"], inline=True)
            embed.add_field(name="Country Code:", value=r["country_code"], inline=True)
            if r["country_code"] == "US":
                embed.add_field(name="State:", value=r["city"], inline=True)
            else:
                embed.add_field(name="City:", value=r["city"], inline=True)
            embed.add_field(name="Flag:", value=r["location"]["country_flag_emoji"], inline=True)
            embed.add_field(name="Continent:", value=r["continent_name"], inline=True)
            try:
                embed.add_field(name="IP Type:", value=r["type"].upper(), inline=True)
            except AttributeError:
                embed.add_field(name="IP Type:", value="None", inline=True)
            embed.set_footer(text="IP information requested by " + str(user))
            embed.add_field(
                name="Proxy Status(Test One):", value=s[f"{ip}"]["proxy"].capitalize(), inline=True
            )
            if s[f"{ip}"]["proxy"] == "yes":
                embed.add_field(name="Proxy Type:", value=s[f"{ip}"]["type"], inline=True)
            if t["result"] == "1":
                embed.add_field(
                    name="Proxy Status(Test Two):", value="Yes".capitalize(), inline=True
                )
            else:
                embed.add_field(
                    name="Proxy Status(Test Two):", value="No".capitalize(), inline=True
                )
            await ctx.send(embed=embed)
            await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        except KeyError:
            await ctx.send("Failed, reached a KeyError.")

    @commands.has_any_role(
        "Management",
        "Senior Administrator",
        "Server Owner",
        "Server Manager",
        "Scripter",
        "Lead Administrator",
    )
    @commands.command(aliases=["vpnchecker", "vpn"])
    async def vpncheck(self, ctx, ip: str):
        """Two tests for proxy usage."""
        vpn1 = "http://proxycheck.io/v2/{}?key=6n5t9m-353305-68f6j3-1qfw04&vpn=1&asn=1&node=1&time=1&inf=0&port=1&seen=1&days=7&tag=msg".format(
            ip
        )
        vpn2 = "http://check.getipintel.net/check.php?ip={}&contact=flare2399@gmail.com&format=json&flags=m".format(
            ip
        )
        r = await self.get(vpn1)
        t = await self.get(vpn2)
        user = ctx.author
        colour = randint(0, 0xFFFFFF)  # Random Hex Value for embed colour.
        embed = discord.Embed(
            title=f"VPN Checker for {ip}",
            colour=discord.Colour(value=colour),
            timestamp=ctx.message.created_at,
        )
        try:
            embed.add_field(
                name="Proxy Status(Test One):", value=r[f"{ip}"]["proxy"].capitalize(), inline=True
            )
            if r[f"{ip}"]["proxy"] == "yes":
                embed.add_field(name="Proxy Type:", value=[f"{ip}"]["type"], inline=True)
            if t["result"] == "1":
                embed.add_field(
                    name="Proxy Status(Test Two):", value="Yes".capitalize(), inline=True
                )
            else:
                embed.add_field(
                    name="Proxy Status(Test Two):", value="No".capitalize(), inline=True
                )
            embed.set_footer(text="VPN information requested by " + str(user))
            await ctx.send(embed=embed)
            message = ctx.message
            await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        except KeyError:
            await ctx.send("Invalid IP")

    @commands.command(pass_context=True)
    @commands.has_permissions(administrator=True)
    async def welcomerules(self, ctx):
        """WC-RP's server rules."""

        embed = discord.Embed(title="West Coast RP Rules", colour=0xFF6A14)
        embed.set_thumbnail(url="http://flareee.com/i/c6duh.png")
        embed.add_field(
            name="Information",
            value="Welcome to the Discord server of **West Coast Role Play**!\n Please make sure that you've read the rules **before** joining!\n\n",
        )
        embed.add_field(
            name="Rules",
            value="**1**. Absolutely NO racism. \n**2**. Keep discussions to relevant text channels.\n**3**. Don't scream / play annoying distorted audio clips in voice channels.\n**4**. Don't play music in voice channels.\n**5**. No spamming\n**6**. English only\n**7**. If you see anyone breaking these rules, please take a screenshot and send it to a moderator\n**8**. No links or images in main chat\n\n\nReact with :white_check_mark: below to be given access to the rest of the server.",
            inline=True,
        )
        await ctx.send(embed=embed)

    @commands.command(pass_context=True)
    @commands.has_permissions(administrator=True)
    async def rules(self, ctx):
        """WC-RP's server rules."""

        embed = discord.Embed(title="West Coast RP Rules", colour=0xFF6A14)
        embed.set_thumbnail(url="http://flareee.com/i/c6duh.png")
        embed.add_field(
            name="Information", value="Welcome to the Discord server of **West Coast Role Play**!"
        )
        embed.add_field(
            name="Rules",
            value="**1**. Absolutely NO racism. \n**2**. Keep discussions to relevant text channels.\n**3**. Don't scream / play annoying distorted audio clips in voice channels.\n**4**. Don't play music in voice channels.\n**5**. No spamming\n**6**. English only\n**7**. If you see anyone breaking these rules, please take a screenshot and send it to a moderator\n**8**. No links or images in main chat\n\n\n",
            inline=True,
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def status(self, ctx):
        try:
            r = "https://api.samp-servers.net/v2/server/server.wc-rp.com:7777"
            req = await self.get(r)
            players = f"{req['core']['pc']}/{req['core']['pm']}"
            ip = req["core"]["ip"]
            online = req["active"]
            if online:
                await ctx.send(
                    "**West Coast Roleplay Status:**\n\n:desktop: IP: {}\n:white_check_mark: Status: **Online**\n:video_game: Players: {}\n:busts_in_silhouette: Community: https://www.wc-rp.com".format(
                        ip, players
                    )
                )
            else:
                await ctx.send("WC-RP is currently offline.")
        except:
            r = "http://monitor.sacnr.com/api/?IP=63.251.20.189&Port=7777&Action=info&Format=json"
            req = await self.get(r)
            players = f"{req['Players']}/400"
            ip = "server.wc-rp.com:7777"
            await ctx.send(
                "**West Coast Roleplay Status:**\n\n:desktop: IP: {}\n:white_check_mark: Status: **Online**\n:video_game: Players: {}\n:busts_in_silhouette: Community: https://www.wc-rp.com".format(
                    ip, players
                )
            )

    @commands.command()
    async def lspd(self, ctx):
        embed = discord.Embed(
            title="WC-RP | Los Santos Police Department",
            colour=0xFF6A14,
            description="Interested in applying for the department or even apply for a firearm license? The Los Santos Police Department is the right place for you to do so, check out the information below for further info.",
        )
        embed.set_thumbnail(
            url="https://vignette.wikia.nocookie.net/lsrp/images/b/bb/Seal_of_the_LSPD.png"
        )
        async with self.config.facs() as leaders:
            embed.add_field(name="Current CoP", value=leaders["lspd"], inline=True)
        embed.add_field(name="Website", value="[Click Here](http://lspd.wc-rp.com)")
        await ctx.send(embed=embed)

    @commands.command()
    async def lsfd(self, ctx):
        embed = discord.Embed(
            title="WC-RP | Los Santos Fire Department",
            colour=0xFF6A14,
            description="Join the Los Santos Fire Department to serve your community well! Become a firefighter and fight fires with us, become a paramedic and attend to medical emergencies! Visit our website listed down below for more information.",
        )
        embed.set_thumbnail(url="https://i.imgur.com/tT4xHgq.png")
        async with self.config.facs() as leaders:
            embed.add_field(name="Current Fire Commissioner", value=leaders["lsfd"], inline=True)
        embed.add_field(name="Website", value="[Click Here](https://forum.ls-fd.org/)")
        embed.set_footer(text="www.ls-fd.org is NOT maintained by the management of WC-RP.")
        await ctx.send(embed=embed)

    @commands.has_any_role(
        "Management",
        "Senior Administrator",
        "Server Owner",
        "Server Manager",
        "Scripter",
        "Lead Administrator",
        "Administrator",
        "Moderator",
    )
    @commands.command()
    async def listplayers(self, ctx):
        """List current in-game players"""
        with SampClient(address="server.wc-rp.com", port=7777) as client:
            t = PrettyTable(["Player", "Level", "Ping"])
            a = []
            for user in client.get_server_clients_detailed():
                if user.score > 0 and "_" not in user.name:
                    name = "'{}'".format(user.name)
                else:
                    name = user.name
                t.add_row([name, user.score, user.ping])
                a.append(user.name)
            for page in pagify(str(t)):
                await ctx.send("```py\n{} players connected\n".format(len(a)) + str(page) + "```")

    @commands.has_any_role(
        "Management",
        "Senior Administrator",
        "Server Owner",
        "Server Manager",
        "Scripter",
        "Lead Administrator",
        "Administrator",
        "Moderator",
    )
    @commands.command()
    async def isonline(self, ctx, name: str):
        """Check if a player is online - case sensitive"""
        with SampClient(address="server.wc-rp.com", port=7777) as client:
            a = []
            for user in client.get_server_clients_detailed():
                if name in str(user.name):
                    a.append(user.name)
            if not a:
                await ctx.send("No matches found")
            else:
                await ctx.send("```" + "\n".join(a) + "```")

    @commands.has_any_role(
        "Management",
        "Senior Administrator",
        "Server Owner",
        "Server Manager",
        "Scripter",
        "Lead Administrator",
        "Administrator",
        "Moderator",
    )
    @commands.guild_only()
    @commands.command()
    async def toggleslow(self, ctx, time: int = 0):
        """
        Slow the chat
        `time` is the time in seconds users must wait after sending a message
        to be able to send another message.
        """
        if time < 0 or time > 120:
            await ctx.send("Invalid time specified! Time must be between 0 and 120 (inclusive)")
            return
        try:
            await ctx.channel.edit(slowmode_delay=time)
        except discord.Forbidden:
            await ctx.send("I am forbidden from doing that.")
            return
        if time > 0:
            await ctx.send(
                "{} is now in slow mode. You may send 1 message "
                "every {} seconds".format(ctx.channel, time)
            )
        else:
            await ctx.send("Slow mode has been disabled for {0.mention}".format(ctx.channel))

    @commands.command(pass_context=True, no_pm=True)
    @commands.has_any_role(
        "Management",
        "Senior Administrator",
        "Server Owner",
        "Server Manager",
        "Scripter",
        "Lead Administrator",
        "Administrator",
        "Moderator",
    )
    async def lockdown(self, ctx, channel: discord.TextChannel = None):
        """Toggles the lockdown mode"""
        role = discord.utils.get(ctx.guild.roles, name="Member")
        if channel is None:
            guild_channel = self.bot.get_channel(461959262961139714)
        else:
            guild_channel = self.bot.get_channel(channel.id)
        overwrite = guild_channel.overwrites_for(role)
        overwrite.update(send_messages=False)
        await guild_channel.set_permissions(
            role, overwrite=overwrite, reason="Lockdown in effect."
        )

        await ctx.send(
            "Channel is locked down. You can unlock the channel by doing {}unlockdown".format(
                ctx.prefix
            )
        )

    @commands.command(pass_context=True, no_pm=True)
    @commands.has_any_role(
        "Management",
        "Senior Administrator",
        "Server Owner",
        "Server Manager",
        "Scripter",
        "Lead Administrator",
        "Administrator",
        "Moderator",
    )
    async def unlockdown(self, ctx, channel: discord.TextChannel = None):
        """Toggles the lockdown mode"""
        role = discord.utils.get(ctx.guild.roles, name="Member")
        if channel is None:
            guild_channel = self.bot.get_channel(461959262961139714)
        else:
            guild_channel = self.bot.get_channel(channel.id)
        overwrite = guild_channel.overwrites_for(role)
        overwrite.update(send_messages=True)
        await guild_channel.set_permissions(role, overwrite=overwrite, reason="Lockdown removed.")

        await ctx.send("Channel is now unlocked.".format(ctx.prefix))

    @commands.command(pass_context=True, no_pm=True)
    @commands.has_any_role(
        "Management",
        "Senior Administrator",
        "Server Owner",
        "Server Manager",
        "Scripter",
        "Lead Administrator",
        "Administrator",
    )
    async def masslockdown(self, ctx):
        """Toggles the lockdown mode"""
        channel_ids = [461959262961139714, 489220160025002014, 462232524043583489]
        role = discord.utils.get(ctx.guild.roles, name="Member")
        for guild_channel in ctx.guild.channels:
            if guild_channel.id in channel_ids:
                overwrite = guild_channel.overwrites_for(role)
                overwrite.update(send_messages=False)
                await guild_channel.set_permissions(
                    role, overwrite=overwrite, reason="Lockdown in effect."
                )

        await ctx.send(
            "Server is locked down. You can unlock the server by doing {}massunlockdown".format(
                ctx.prefix
            )
        )

    @commands.command(no_pm=True)
    @commands.has_any_role(
        "Management",
        "Senior Administrator",
        "Server Owner",
        "Server Manager",
        "Scripter",
        "Lead Administrator",
        "Administrator",
    )
    async def massunlockdown(self, ctx):
        """Toggles the lockdown mode"""
        channel_ids = [461959262961139714, 489220160025002014, 462232524043583489]
        role = discord.utils.get(ctx.guild.roles, name="Member")
        for guild_channel in ctx.guild.channels:
            if guild_channel.id in channel_ids:
                overwrite = guild_channel.overwrites_for(role)
                overwrite.update(send_messages=True)
                await guild_channel.set_permissions(
                    role, overwrite=overwrite, reason="Lockdown in effect."
                )

        await ctx.send("Server is now unlocked. ")

    @commands.command()
    @commands.has_any_role(
        "Management",
        "Senior Administrator",
        "Server Owner",
        "Server Manager",
        "Scripter",
        "Lead Administrator",
        "Faction Administrator",
    )
    async def addleader(self, ctx, faction: str, *, chief: str):
        """Add a new chief to the embed."""
        async with self.config.facs() as leaders:
            leaders[faction] = chief
            await ctx.send("Done.")
