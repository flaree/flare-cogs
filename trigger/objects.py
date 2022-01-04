import datetime
import random


class TriggerObject:
    def __init__(self, **kwargs) -> None:
        self.trigger = kwargs.get("name")
        self.trigger = kwargs.get("trigger", None)
        self.responses = kwargs.get("responses", None)
        self.owner = kwargs.get("owner", None)
        self.guild = kwargs.get("guild", None)
        self.cooldown = kwargs.get("cooldown", 0)
        self.timestamp = None
        self.uses = kwargs.get("uses", 0)
        self.toggle = kwargs.get("toggle", False)
        self.case_sensitive = kwargs.get("case_sensitive", True)

    def check(self, message):
        if not self.toggle:
            return False

        trigger = self.trigger
        content = message.content
        if not self.case_sensitive:
            trigger = trigger.lower()
            content = content.lower()

        if trigger in content:
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
            return True
        return False

    async def respond(self, channel):
        response = random.choice(self.responses)
        self.uses += 1
        self.timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
        await channel.send(response)

    def __repr__(self) -> str:
        return f"<TriggerObject trigger={self.trigger}>"
