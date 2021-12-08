import asyncio
import functools
from typing import List, Union

import discord
from redbot.core import commands
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate


# Code taken from Red-DiscordBot repo, adapted to support replies.
async def menu(
    ctx: commands.Context,
    pages: Union[List[str], List[discord.Embed]],
    controls: dict,
    message: discord.Message = None,
    page: int = 0,
    timeout: float = 30.0,
    **kwargs,
):
    """
    An emoji-based menu
    .. note:: All pages should be of the same type
    .. note:: All functions for handling what a particular emoji does
              should be coroutines (i.e. :code:`async def`). Additionally,
              they must take all of the parameters of this function, in
              addition to a string representing the emoji reacted with.
              This parameter should be the last one, and none of the
              parameters in the handling functions are optional
    Parameters
    ----------
    ctx: commands.Context
        The command context
    pages: `list` of `str` or `discord.Embed`
        The pages of the menu.
    controls: dict
        A mapping of emoji to the function which handles the action for the
        emoji.
    message: discord.Message
        The message representing the menu. Usually :code:`None` when first opening
        the menu
    page: int
        The current page number of the menu
    timeout: float
        The time (in seconds) to wait for a reaction
    Raises
    ------
    RuntimeError
        If either of the notes above are violated
    """
    if not isinstance(pages[0], (discord.Embed, str)):
        raise RuntimeError("Pages must be of type discord.Embed or str")
    if not all(isinstance(x, discord.Embed) for x in pages) and not all(
        isinstance(x, str) for x in pages
    ):
        raise RuntimeError("All pages must be of the same type")
    for key, value in controls.items():
        maybe_coro = value
        if isinstance(value, functools.partial):
            maybe_coro = value.func
        if not asyncio.iscoroutinefunction(maybe_coro):
            raise RuntimeError("Function must be a coroutine")
    current_page = pages[page]

    if not message:
        if isinstance(current_page, discord.Embed):
            message = await ctx.send(embed=current_page, **kwargs)
        else:
            message = await ctx.send(current_page, **kwargs)
        # Don't wait for reactions to be added (GH-1797)
        # noinspection PyAsyncCall
        start_adding_reactions(message, controls.keys())
    else:
        try:
            if isinstance(current_page, discord.Embed):
                await message.edit(embed=current_page, **kwargs)
            else:
                await message.edit(content=current_page, **kwargs)
        except discord.NotFound:
            return

    try:
        predicates = ReactionPredicate.with_emojis(tuple(controls.keys()), message, ctx.author)
        tasks = [
            asyncio.ensure_future(ctx.bot.wait_for("reaction_add", check=predicates)),
            asyncio.ensure_future(ctx.bot.wait_for("reaction_remove", check=predicates)),
        ]
        done, pending = await asyncio.wait(
            tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()

        if len(done) == 0:
            raise asyncio.TimeoutError()
        react, user = done.pop().result()
    except asyncio.TimeoutError:
        if not ctx.me:
            return
        try:
            if message.channel.permissions_for(ctx.me).manage_messages:
                await message.clear_reactions()
            else:
                raise RuntimeError
        except (discord.Forbidden, RuntimeError):  # cannot remove all reactions
            for key in controls.keys():
                try:
                    await message.remove_reaction(key, ctx.bot.user)
                except discord.Forbidden:
                    return
                except discord.HTTPException:
                    pass
        except discord.NotFound:
            return
    else:
        return await controls[react.emoji](
            ctx, pages, controls, message, page, timeout, react.emoji
        )
