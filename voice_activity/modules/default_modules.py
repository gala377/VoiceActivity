import textwrap

from typing import Sequence

from voice_activity.abc import (
    AbstractPlugin,
    AbstractCommand,
)


class DefaultModulesPlugin(AbstractPlugin):

    def __init__(self, bot, *args, **kwargs):
        bot.add_module(HelpCommand)


class HelpMixin:
    def description(self) -> str:
        raise NotImplementedError


class HelpCommand(AbstractCommand, HelpMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_help = None

    def name(self) -> str:
        return "help"

    def description(self):
        return "shows this message"

    async def run(self, ctx):
        resp_chan = ctx['resp_chan']
        if self._cached_help is None:
            self._cached_help = self._compute_help_msg()
        await resp_chan.send(self._cached_help)

    def _compute_help_msg(self):
        descriptions = {
            cmd: inst.description() for cmd, inst in self._bot._bot_commands.items()
            if isinstance(inst, HelpMixin)
        }
        msg = f"bot serves you with\n```"
        for cmd, desc in descriptions.items():
            msg += f"\n{cmd:<12} - "
            if not isinstance(desc, (str, Sequence)) or not desc:
                msg += " empty or invalid help"
                continue
            msg += self._split_and_indent_lines(desc)
        msg += "```"
        return msg

    def _split_and_indent_lines(self, desc):
        if not isinstance(desc, str):
            desc = "\n".join(desc)
        else:
            desc = self._skip_first_line_if_empty(desc)
        desc = textwrap.fill(textwrap.dedent(desc), replace_whitespace=False)
        first_line = True
        def pred(line):
            nonlocal first_line
            if first_line:
                first_line = False
                return False
            return line.strip()
        return textwrap.indent(desc, " "*15, pred)

    def _skip_first_line_if_empty(self, text):
        lines = text.splitlines()
        if not lines[0]:
            lines = lines[1:]
        return "\n".join(lines)