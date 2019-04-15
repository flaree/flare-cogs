import discord
from redbot.core import commands, checks    
from redbot.core.utils.chat_formatting import pagify
from random import randint, choice
from samp_client.client import SampClient
import aiohttp
import asyncio
from prettytable import PrettyTable

BaseCog = getattr(commands, "Cog", object)


class Mrp(BaseCog):
    """MRP's Commands"""

    def __init__(self, bot):
        self.bot = bot
        self._session = aiohttp.ClientSession()

    async def __unload(self):
        asyncio.get_event_loop().create_task(self._session.close())

    async def get(self, url):
        async with self._session.get(url) as response:
            return await response.json()

    #    async def on_member_update(self, before, after):
    #       channel = self.bot.get_channel(537310109181673492)
    #      r = "https://api.samp-servers.net/v2/server/server.wc-rp.com:7777"
    #     req = await self.get(r)
    #    players = int(f"{req['core']['pc']}")
    #   if players < 10:
    #      u10 = str(channel.name[17:18])
    # else:
    #    u10 = str(channel.name[17:19])
    # if u10 != str(players):
    #   playerss = f"Current Players: {players}/400"
    #  await channel.edit(name=f"{playerss}")

    @commands.command(aliases=["serverip", "ips", "mrp", "m-rp", "site", "website", "forum", "forums"])
    async def ip(self, ctx):
        """MRP's server IP."""
        # r = "https://api.samp-servers.net/v2/server/server.wc-rp.com:7777"
        # req = await self.get(r)
        # version = f"{req['core']['gm']}"
        # samp = f"{req['core']['vn']}"
        embed = discord.Embed(title="Metropolis Roleplay Information", colour=0xff0000)
        embed.add_field(name="IP", value="put ip here", inline=True)
        embed.add_field(name="Numerical IP", value="put ip here", inline=True)
        embed.add_field(name="SA-MP Version", value="0.3DL", inline=True)
        embed.add_field(name="Forums", value="https://website.com", inline=True)
        embed.add_field(name="Discord Invite Link", value="https://discord.gg/link", inline=True)
        embed.add_field(name="Server Version", value="idfk", inline=True)
        embed.set_footer(text="M-RP | 2019 - ! ")
        await ctx.send(embed=embed)

    @commands.has_any_role("management", "admin", "lead admin", "tester", "developer")
    @commands.command()
    async def iplookup(self, ctx, ip: str):
        """IPLookup API"""
        ip1 = "http://api.ipstack.com/{}?access_key=6c5ddc76ac6b10405123ac249aff6bf8&format=1".format(ip)
        ip2 = "http://proxycheck.io/v2/{}?key=6n5t9m-353305-68f6j3-1qfw04&vpn=1&asn=1&node=1&time=1&inf=0&port=1&seen=1&days=7&tag=msg".format(
            ip)
        ip3 = "http://check.getipintel.net/check.php?ip={}&contact=flare2399@gmail.com&format=json&flags=m".format(ip)
        r = await self.get(ip1)
        s = await self.get(ip2)
        t = await self.get(ip3)
        user = ctx.author
        message = ctx.message
        colour = randint(0, 0xFFFFFF)  # Random Hex Value for embed colour.
        try:
            embed = discord.Embed(title=f"IP Lookup Information for {ip}", colour=discord.Colour(value=colour),
                                  timestamp=ctx.message.created_at)
            embed.add_field(name="Country:", value=r['country_name'], inline=True)
            embed.add_field(name="Country Code:", value=r['country_code'], inline=True)
            if r['country_code'] == "US":
                embed.add_field(name="State:", value=r['city'], inline=True)
            else:
                embed.add_field(name="City:", value=r['city'], inline=True)
            embed.add_field(name="Flag:", value=r['location']['country_flag_emoji'], inline=True)
            embed.add_field(name="Continent:", value=r['continent_name'], inline=True)
            try:
                embed.add_field(name="IP Type:", value=r['type'].upper(), inline=True)
            except AttributeError:
                embed.add_field(name="IP Type:", value="None", inline=True)
            embed.set_footer(
                text="IP information requested by " + str(user))
            embed.add_field(name="Proxy Status(Test One):", value=s[f'{ip}']['proxy'].capitalize(), inline=True)
            if s[f'{ip}']['proxy'] == "yes":
                embed.add_field(name="Proxy Type:", value=s[f'{ip}']['type'], inline=True)
            if t['result'] == "1":
                embed.add_field(name="Proxy Status(Test Two):", value="Yes".capitalize(), inline=True)
            else:
                embed.add_field(name="Proxy Status(Test Two):", value="No".capitalize(), inline=True)
            await ctx.send(embed=embed)
            await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        except KeyError:
            await ctx.send("Failed, reached a KeyError.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def welcomerules(self, ctx):
        """M-RP's server rules."""

        embed = discord.Embed(title="Metropolis RP", colour=0xff0000)
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/543573723442053140/560149233244700673/2.png")
        embed.add_field(name="Information",
                        value="Welcome to the Discord server of **Metropolis Role Play**!\n Please make sure that you've read the rules **before** joining!\n\n")
        embed.add_field(name="Rules",
                        value="Be respectful to everyone at all times.\nUse the correct channel that is specific to certain chat content. \nUse English in all channels.\nUse common sense when necessary.\n\nDo not repeatedly spam and mention/poke people.\nDo not mention usergroups (roles) in any public channels.\nDo not advertise any third party services or Discord servers.\nDo not impose as other community members.\nDo not discuss any pending ban appeals.\n\nNOTE: Forum and server rules still apply to this Discord server.\nBreach of the ruleset above will result in some form of punishment, depending on staff judgement.", 
                            inline=True)
        embed.set_footer(text="React with the emoji below to gain entry into the server.")
        await ctx.send(embed=embed)

    #    @commands.command()
    #   async def status(self, ctx):
    #      try:
    #         r = "https://api.samp-servers.net/v2/server/server.wc-rp.com:7777"
    #        req = await self.get(r)
    #       players = f"{req['core']['pc']}/{req['core']['pm']}"
    #      ip = req['core']['ip']
    #     online = req['active']
    #    if online:
    #       await ctx.send(
    #          "**West Coast Roleplay Status:**\n\n:desktop: IP: {}\n:white_check_mark: Status: **Online**\n:video_game: Players: {}\n:busts_in_silhouette: Community: https://www.wc-rp.com".format(
    #             ip, players))
    # else:
    #   await ctx.send("WC-RP is currently offline.")
    # except:
    #   r = "http://monitor.sacnr.com/api/?IP=63.251.20.189&Port=7777&Action=info&Format=json"
    #  req = await self.get(r)
    # players = f"{req['Players']}/400"
    # ip = "server.wc-rp.com:7777"
    # await ctx.send(
    #   "**West Coast Roleplay Status:**\n\n:desktop: IP: {}\n:white_check_mark: Status: **Online**\n:video_game: Players: {}\n:busts_in_silhouette: Community: https://www.wc-rp.com".format(
    #      ip, players))


    #@commands.has_any_role("Management", "Senior Administrator", "Server Owner", "Server Manager", "Scripter",
     #                      "Lead Administrator", "Administrator", "Moderator")
    # @commands.command()
    # async def listplayers(self, ctx):
    #   """List current in-game players"""
    #  with SampClient(address="server.wc-rp.com", port=7777) as client:
    #     t = PrettyTable(["Player", "Level", "Ping"])
    #    a = []
    #   for user in client.get_server_clients_detailed():
    #      if user.score > 0 and "_" not in user.name:
    #         name = "'{}'".format(user.name)
    #    else:
    #       name = user.name
    #  t.add_row([name, user.score, user.ping])
    # a.append(user.name)
    #  for page in pagify(str(t)):
    #     await ctx.send("```py\n{} players connected\n".format(len(a)) + str(page) + "```")

    #    @commands.has_any_role("Management", "Senior Administrator", "Server Owner", "Server Manager", "Scripter",
    #                          "Lead Administrator", "Administrator", "Moderator")
    #  @commands.command()
    # async def isonline(self, ctx, name: str):
    #    """Check if a player is online - case sensitive"""
    #   with SampClient(address="server.wc-rp.com", port=7777) as client:
    #      a = []
    #     for user in client.get_server_clients_detailed():
    #        if name in str(user.name):
    #           a.append(user.name)
    #  if not a:
    #     await ctx.send("No matches found")
    # else:
    #   await ctx.send("```" + "\n".join(a) + "```")

    @commands.has_any_role("management", "admin", "lead admin", "developer")
    @commands.guild_only()
    @commands.command()
    async def toggleslow(self, ctx, time: int = 0):
        """
        Slow the chat
        `time` is the time in seconds users must wait after sending a message
        to be able to send another message.
        """
        if time < 0 or time > 21600:
            await ctx.send("Invalid time specified! Time must be between 0 and 21600 (inclusive)")
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

    @commands.has_any_role("management", "admin", "lead admin", "developer")
    async def lockdown(self, ctx, channel: discord.TextChannel = None):
        """Toggles the lockdown mode"""
        role = discord.utils.get(ctx.guild.roles, name="verified")
        if channel is None:
            guild_channel = self.bot.get_channel(558999197366484995)
        else:
            guild_channel = self.bot.get_channel(channel.id)
        overwrite = guild_channel.overwrites_for(role)
        overwrite.update(send_messages=False)
        await guild_channel.set_permissions(
            role,
            overwrite=overwrite,
            reason="Lockdown in effect.")

        await ctx.send(
            "Channel is locked down. You can unlock the channel by doing {}unlockdown".format(
                ctx.prefix
            )
        )

    @commands.command(pass_context=True, no_pm=True)
    @commands.has_any_role("management", "admin", "lead admin", "developer")
    async def unlockdown(self, ctx, channel: discord.TextChannel = None):
        """Toggles the lockdown mode"""
        role = discord.utils.get(ctx.guild.roles, name="verified")
        if channel is None:
            guild_channel = self.bot.get_channel(558999197366484995)
        else:
            guild_channel = self.bot.get_channel(channel.id)
        overwrite = guild_channel.overwrites_for(role)
        overwrite.update(send_messages=True)
        await guild_channel.set_permissions(
            role,
            overwrite=overwrite,
            reason="Lockdown removed.")

        await ctx.send(
            "Channel is now unlocked.".format(
                ctx.prefix
            )
        )

    @commands.command(pass_context=True, no_pm=True)
    @commands.has_any_role("management", "lead admin")
    async def masslockdown(self, ctx):
        """Toggles the lockdown mode"""
        channel_ids = [558999197366484995, 559019205408587786, 559018970909376551, 559018822582009867]
        role = discord.utils.get(ctx.guild.roles, name="verified")
        for guild_channel in ctx.guild.channels:
            if guild_channel.id in channel_ids:
                overwrite = guild_channel.overwrites_for(role)
                overwrite.update(send_messages=False)
                await guild_channel.set_permissions(
                    role,
                    overwrite=overwrite,
                    reason="Lockdown in effect.")

        await ctx.send(
            "Server is locked down. You can unlock the server by doing {}massunlockdown".format(
                ctx.prefix
            )
        )

    @commands.command(no_pm=True)
    @commands.has_any_role("management", "lead admin", "developer")
    async def massunlockdown(self, ctx):
        """Toggles the lockdown mode"""
        channel_ids = [558999197366484995, 559019205408587786, 559018970909376551, 559018822582009867]
        role = discord.utils.get(ctx.guild.roles, name="verified")
        for guild_channel in ctx.guild.channels:
            if guild_channel.id in channel_ids:
                overwrite = guild_channel.overwrites_for(role)
                overwrite.update(send_messages=True)
                await guild_channel.set_permissions(
                    role,
                    overwrite=overwrite,
                    reason="Lockdown in effect.")

        await ctx.send(
            "Server is now unlocked. "
        )
