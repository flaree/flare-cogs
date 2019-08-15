from redbot.core import commands, Config, checks
import discord
import aiohttp
import asyncio
from redbot.core.data_manager import bundled_data_path


import hashlib
from .stuff import pokemons


class PokecordNotifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=145519400223506432)
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        defaults = {"notify": {}}
        self.config.register_global(**defaults)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def get(self, thing):
        async with self.session.get(thing) as response:
            return await response.read()

    async def find_pokemon(self, thing):
        stuff = await self.get(thing)
        h = hashlib.md5(stuff).hexdigest()
        for x in pokemons:
            if x["hash"] == h:
                return x["name"]

    @checks.is_owner()
    @commands.command()
    async def pokenotify(self, ctx, user: discord.Member, *, pokemon):
        """Add a pokemon to your notify list."""
        async with self.config.notify() as notify:
            if pokemon in notify:
                if user.id in notify[pokemon]:
                    notify[pokemon].remove(user.id)
                    await ctx.send("Removed that notif.")
                else:
                    notify[pokemon].append(user.id)
                    await ctx.send("Notif added")
            else:
                notify[pokemon] = []
                notify[pokemon].append(user.id)
                await ctx.send("Notif added")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == 365975655608745985:
            if message.embeds:
                if "A wild" in message.embeds[0].title:
                    url = message.embeds[0].image.url
                    na = await self.find_pokemon(url)
                    await asyncio.sleep(0.5)
                    notifs = await self.config.notify()
                    if na in notifs:
                        for userid in notifs:
                            user = self.bot.get_user(userid)
                            if user is not None and user in message.guild.members:

                                await user.send(
                                    f"A `{na}` has spawned in {message.guild}. Be quick.\n{message.jump_url}"
                                )
