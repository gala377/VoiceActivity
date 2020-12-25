from typing import Sequence

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
            if not isinstance(desc, Sequence) or not desc:
                msg += " empty or invalid help"
                continue
            msg += desc[0]
            for line in desc[1:]:
                msg += f'{(" "*23)}{line}'
        await resp_chan.send(msg)


class HelpMixin:
    def description(self) -> Sequence[str]:
        raise NotImplementedError
