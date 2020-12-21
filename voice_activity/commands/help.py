from voice_activity.commands.abc import AbstractCommand

class HelpCommand(AbstractCommand):

    @classmethod
    def name(cls) -> str:
        return "help"

    async def run(self, ctx):
        resp_chan = ctx['resp_chan']
        await resp_chan.send("sub/unsub channel_name")
