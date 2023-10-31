from typing import Any, Dict, List

import TagScriptEngine as tse
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number

kick_message: str = "Done. That felt good."
ban_message: str = "Done. That felt good."
tempban_message: str = "Done. Enough chaos for now."
unban_message: str = "Unbanned the user from this server."

TAGSCRIPT_LIMIT: int = 10_000

blocks: List[tse.Block] = [
    tse.LooseVariableGetterBlock(),
    tse.AssignmentBlock(),
    tse.EmbedBlock(),
]

tagscript_engine: tse.Interpreter = tse.Interpreter(blocks)


def process_tagscript(content: str, seed_variables: Dict[str, tse.Adapter] = {}) -> Dict[str, Any]:
    output: tse.Response = tagscript_engine.process(content, seed_variables)
    kwargs: Dict[str, Any] = {}
    if output.body:
        kwargs["content"] = output.body[:2000]
    if embed := output.actions.get("embed"):
        kwargs["embed"] = embed
    return kwargs


def validate_tagscript(tagscript: str) -> bool:
    length = len(tagscript)
    if length > TAGSCRIPT_LIMIT:
        raise TagCharacterLimitReached(TAGSCRIPT_LIMIT, length)
    return True


class TagError(Exception):
    """Base exception class."""


class TagCharacterLimitReached(TagError):
    """Taised when the Tagscript character limit is reached."""

    def __init__(self, limit: int, length: int):
        super().__init__(
            f"Tagscript cannot be longer than {humanize_number(limit)} (**{humanize_number(length)}**)."
        )


class TagScriptConverter(commands.Converter[str]):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        try:
            validate_tagscript(argument)
        except TagError as e:
            raise commands.BadArgument(str(e))
        return argument
