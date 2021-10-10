from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES


class Jishaku(*STANDARD_FEATURES, *OPTIONAL_FEATURES):
    """Jishaku ported to Red"""

    __version__ = "0.0.1"
    __author__ = "flare#0001, Gorialis"

    def format_help_for_context(self, ctx):
        """Thanks Sinbad."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    jsk_load = None
    jsk_unload = None
    jsk_shutdown = None
