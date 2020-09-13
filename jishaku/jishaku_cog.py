from jishaku.cog import JishakuBase, jsk
from jishaku.metacog import GroupCogMeta


class Jishaku(JishakuBase, metaclass=GroupCogMeta, command_parent=jsk):
    """Jishaku ported to Red"""

    __version__ = "0.0.1"
    __author__ = "flare#0001"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    jsk_load = None
    jsk_unload = None
    jsk_shutdown = None
