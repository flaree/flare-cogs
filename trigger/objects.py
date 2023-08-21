import datetime
import random
import re


class TriggerObject:
    def __init__(self, **kwargs) -> None:
        self.trigger_name = kwargs.get("name")
        self.trigger = kwargs.get("trigger", None)
        self.responses = kwargs.get("responses", None)
        self.owner = kwargs.get("owner", None)
        self.guild = kwargs.get("guild", None)
        self.cooldown = kwargs.get("cooldown", 0)
        self.timestamp = None
        self.uses = kwargs.get("uses", 0)
        self.toggle = kwargs.get("toggle", False)
        self.case_sensitive = kwargs.get("case_sensitive", True)
        self.word_boundary = kwargs.get("word_boundary", False)
        self.embed_search = kwargs.get("embed_search", False)
        self.pattern = None

    def check(self, message):
        if not self.toggle:
            return False

        trigger = self.trigger
        content = message.content
        if not self.case_sensitive:
            trigger = trigger.lower()
            content = content.lower()

        if self.cooldown > 0:
            if self.timestamp is None:
                self.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
            else:
                now = datetime.datetime.now(tz=datetime.timezone.utc)
                diff = now - self.timestamp
                if diff.total_seconds() < self.cooldown:
                    return False
                else:
                    self.timestamp = now

        if self.word_boundary:
            if self.pattern is None:
                self.pattern = re.compile(rf"\b{re.escape(self.trigger.lower())}\b", flags=re.I)
            if self.pattern.search(content):
                return True
        elif trigger in content:
            return True
        elif self.embed_search:
            embeds = message.embeds
            if len(embeds) > 0:
                embed_dict_list = []
                for embed in embeds:
                    embed_dict_list.append(embed.to_dict())
                if self.pattern is None:
                    self.pattern = re.compile(rf"{re.escape(self.trigger.lower())}", flags=re.I)
                if self.pattern.search(str(embed_dict_list)):
                    return True
        return False

    async def respond(self, message):
        response = random.choice(self.responses)
        self.uses += 1
        self.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        objects = {
            "user": message.author,
            "uses": self.uses,
            "channel": message.channel,
            "guild": message.guild,
            "message": message,
            "trigger": self.trigger_name,
        }
        resp = self.transform_message(response, objects)
        await message.channel.send(resp)

    def __repr__(self) -> str:
        return f"<TriggerObject trigger={self.trigger}>"

    # https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/customcom/customcom.py#L824
    @staticmethod
    def transform_parameter(result, objects) -> str:
        """
        For security reasons only specific objects are allowed
        Internals are ignored
        """
        raw_result = "{" + result + "}"
        if result in objects:
            return str(objects[result])
        try:
            first, second = result.split(".")
        except ValueError:
            return raw_result
        if first in objects and not second.startswith("_"):
            first = objects[first]
        else:
            return raw_result
        return str(getattr(first, second, raw_result))

    def transform_message(self, message, objects):
        results = re.findall(r"{([^}]+)\}", message)
        for result in results:
            param = self.transform_parameter(result, objects)
            message = message.replace("{" + result + "}", param)
        return message
