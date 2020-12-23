import asyncio
import re
import logging
import types
import inspect
import sys

import discord
from stdlib_list import stdlib_list

import voice_activity
from voice_activity.abc import (
    AbstractCommand,
    AbstractListener,
    AbstractPlugin,
)


USER_CTX_TIMEOUT = 1200 # in seconds

COMMAND_REGEX = re.compile(r'([^"].*?|".*?")(?:\s|$)')

LOGGER = logging.getLogger(__name__)
PYTHON_VERSION = f"{sys.version_info[0]}.{sys.version_info[1]}"
EXCLUDE_FROM_AUTODISCOVERY = {"discord"} | set(dir(__builtins__)) | set(sys.builtin_module_names) | set(stdlib_list(PYTHON_VERSION))

class VoiceActivity(discord.Client):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._users_context = {}
        self._bot_commands = {}
        self._bot_listeners = []
        self._registered_plugins = set()

    def autodiscover_plugins(self, mod, visited_modules=None):
        if not inspect.ismodule(mod):
            raise ValueError(f"Autodiscovery can only be done on modules. Passed {mode}")

        keys = [k for k in vars(mod) if not k.startswith("_") and not k in EXCLUDE_FROM_AUTODISCOVERY]
        if visited_modules is None:
            visited_modules = set()
        visited_modules.add(mod)
        for k in keys:
            val = vars(mod)[k]
            if inspect.ismodule(val) and not val in visited_modules:
                self.autodiscover_plugins(val, visited_modules)
            elif isinstance(val, type) and issubclass(val, AbstractPlugin):
                autodiscover = (
                    not val in self._registered_plugins
                    and val.auto_discovery
                    and not "Abstract" in val.__name__)
                if not autodiscover:
                    continue
                plug = val(self)
                self._registered_plugins.add(val)
                LOGGER.info(
                    "Adding plugin %s from module: %s",
                    plug.__class__.__name__,
                    mod.__package__)

    def add_module(self, mod_cls, *args, **kwargs):
        objs = []
        module_types = (AbstractCommand, AbstractPlugin, AbstractListener)
        if inspect.ismodule(mod_cls):
            objs.extend(
                v for k, v in vars(mod_cls).items()
                if isinstance(v, type)
                and issubclass(v, module_types)
                and not k.startswith("_")
                and not "Abstract" in k)
        else:
            objs.append(mod_cls)
        for mod in objs:
            obj = mod(self, *args, **kwargs)
            if isinstance(obj, AbstractCommand):
                self._bot_commands[obj.name()] = obj
            if isinstance(obj, AbstractListener):
                self._bot_listeners.append(obj)

    async def _in_chan_callout(self, message):
        reply = message.author
        if reply.id not in self._users_context:
            self._users_context[reply.id] = reply
            asyncio.create_task(self._remove_context(reply.id))
        await reply.send("What do you want from me?")

    async def _run_cmd(self, user, guild, resp_chan, content):
        try:
            cmd, args = self._parse_cmd(content)
            LOGGER.info("got command %s from user %s", cmd, user.name)
            cmd = self._bot_commands.get(cmd, self._unknown_command)
            ctx = {"user": user, "guild": guild, "resp_chan": resp_chan}
            LOGGER.info("invoking command %s for user %s", cmd, user.name)
            await cmd(ctx, *args)
        except Exception as e:
            LOGGER.info("couldn't parse command %a", e)
            await resp_chan.send(str(e))

    def _parse_cmd(self, mess):
        """
        Here we should parse command and its arguments.
        If anything is wrong (for example number of arguments
        for the command does not match) then exception should
        be raised.
        """
        try:
            LOGGER.debug("parsing message: '%s'", mess)
            ment, *rest = mess.split(" ")
            if ment == f"@{self.user.name}":
                mess = " ".join(rest).strip()
            matches = COMMAND_REGEX.findall(mess)
            matches = [x.strip('"') for x in matches]
            cmd, *args = matches
        except ValueError:
            raise ValueError("wrong command format, expected `cmd arg2 arg2...`")
        return cmd, args

    async def _unknown_command(self, ctx, *args):
        LOGGER.info("got unknown command from user %s", ctx['user'].name)
        await ctx["resp_chan"].send("Unknown command, maybe try `help`?")

    async def on_message(self, message):
        LOGGER.debug("got new message: '%s' from '%s' guild is '%s'", message.content, message.author.name, message.guild)
        prevent_default = False
        for listener in self._bot_listeners:
            res = await listener.on_message(message)
            prevent_default = prevent_default or (res is not None and res)
        if prevent_default:
            return
        if message.author == self.user:
            LOGGER.debug("got self message")
            return
        elif message.guild is not None and self.user in message.mentions:
            LOGGER.debug("message: '%s' in guild", message.clean_content)
            if message.clean_content.strip() == f"@{self.user.name}":
                LOGGER.debug("called from guild by %s", message.author.name)
                await self._in_chan_callout(message)
            else:
                LOGGER.debug("got cmd in guild from %s", message.author.name)
                await self._run_cmd(message.author, message.guild, message.channel, message.clean_content)
        elif message.guild is None:
            LOGGER.debug("got priv message: '%s' from '%s'", message.content, message.author.name)
            ctx = self._users_context.get(message.author.id)
            if ctx is None:
                LOGGER.debug("no context found for user %s", message.author.name)
                await message.author.send(
                    "sorry, could you call me from the server you want to execute commands in.")
            else:
                LOGGER.debug("got context for user %s. Running command.", message.author.name)
                dm_chan = message.author.dm_channel
                if dm_chan is None:
                    dm_chan = await message.author.create_dm()
                await self._run_cmd(message.author, ctx.guild, dm_chan, message.content)
        LOGGER.debug("message not important for me")

    async def on_voice_state_update(self, mem, bef, after):
        for listener in self._bot_listeners:
            await listener.on_voice_state_update(mem, bef, after)

    async def _remove_context(self, user_id):
        await asyncio.sleep(USER_CTX_TIMEOUT)
        LOGGER.debug("removing user %a context", user_id)
        del self._users_context[user_id]


def create_bot():
    bot = VoiceActivity()
    bot.autodiscover_plugins(voice_activity.modules)
    return bot
