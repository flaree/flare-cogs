import contextlib

import discord
from redbot.core import commands
from redbot.core.utils.menus import menu


async def match_info(
    ctx: commands.Context,
    pages: list,
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
    perms = message.channel.permissions_for(ctx.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        with contextlib.suppress(discord.NotFound):
            await message.remove_reaction(emoji, ctx.author)
    command = ctx.bot.get_command("faceit match")
    await ctx.send("Click the X on the match menu to return to the menu before.", delete_after=20)
    await ctx.invoke(command, match_id=message.embeds[0].to_dict()["fields"][0]["value"])
    return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


async def account_stats(
    ctx: commands.Context,
    pages: list,
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
    perms = message.channel.permissions_for(ctx.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        with contextlib.suppress(discord.NotFound):
            await message.remove_reaction(emoji, ctx.author)
    command = ctx.bot.get_command("faceit stats")
    await ctx.send(
        "Click the X on the in-depth statistics to return to the menu before.", delete_after=20
    )
    embed = message.embeds[0].to_dict()
    await ctx.invoke(
        command,
        game=message.embeds[0].to_dict()["fields"][3]["name"].lower(),
        user=embed["author"]["name"],
    )
    return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


async def account_matches(
    ctx: commands.Context,
    pages: list,
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
    perms = message.channel.permissions_for(ctx.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        with contextlib.suppress(discord.NotFound):
            await message.remove_reaction(emoji, ctx.author)
    command = ctx.bot.get_command("faceit matches")
    await ctx.send(
        "Click the X on the in-depth stat statistics to return to the menu before.",
        delete_after=20,
    )
    embed = message.embeds[0].to_dict()
    await ctx.invoke(command, user=embed["author"]["name"])
    return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


async def account_ongoing(
    ctx: commands.Context,
    pages: list,
    controls: dict,
    message: discord.Message,
    page: int,
    timeout: float,
    emoji: str,
):
    perms = message.channel.permissions_for(ctx.me)
    if perms.manage_messages:  # Can manage messages, so remove react
        with contextlib.suppress(discord.NotFound):
            await message.remove_reaction(emoji, ctx.author)
    command = ctx.bot.get_command("faceit ongoing")
    embed = message.embeds[0].to_dict()
    await ctx.invoke(command, user=embed["author"]["name"])
    return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)
