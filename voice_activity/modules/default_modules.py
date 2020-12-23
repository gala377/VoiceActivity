from voice_activity.abc import (
    AbstractPlugin,
    AbstractCommand,
)


class DefaultModulesPlugin(AbstractPlugin):

    def __init__(self, bot, *args, **kwargs):
        bot.add_module(HelpCommand)


class HelpCommand(AbstractCommand):

    def name(self) -> str:
        return "help"

    async def run(self, ctx):
        resp_chan = ctx['resp_chan']
        await resp_chan.send("sub/unsub channel_name")


