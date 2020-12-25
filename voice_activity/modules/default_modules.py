import textwrap

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
        descriptions = {
            cmd: inst.description() for cmd, inst in self._bot._bot_commands.items()
            if isinstance(inst, HelpMixin)
        }
        msg = f"{self._bot.name()} bot serves you with\n"
        for cmd, desc in descriptions.items():
            msg += f"\n{cmd:<20} -"
            if not isinstance(desc, str) or not desc:
                msg += " empty or invalid help"
                continue
            desc = textwrap.fill(textwrap.dedent(msg))
            desc = msg.splitlines()
            msg += desc[0]
            msg += textwrap.indent(desc[1:], " "*23)
        await resp_chan.send(msg)


class HelpMixin:
    def description(self) -> str:
        raise NotImplementedError
