import jishaku
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES

jishaku.Flags.RETAIN = True
jishaku.Flags.NO_DM_TRACEBACK = True
jishaku.Flags.FORCE_PAGINATOR = True


class Jishaku(*STANDARD_FEATURES, *OPTIONAL_FEATURES):
    """Jishaku ported to Red"""

    __version__ = "0.0.2, Jishaku {}".format(jishaku.__version__)
    __author__ = "flare#0001, Gorialis"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}\nAuthor: {self.__author__}"

    jsk_load = None
    jsk_unload = None
    jsk_shutdown = None
