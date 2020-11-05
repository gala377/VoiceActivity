from voice_activity.commands.abc import AbstractCommand

class HelpCommand(AbstractCommand):

    @classmethod
    def name(cls) -> str:
        return "help"

    async def run(self, ctx):
        user = ctx['user']
        await user.send("sub/unsub channel_name")
