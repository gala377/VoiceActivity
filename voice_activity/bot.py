import discord
import asyncio
import re
import logging

from voice_activity import commands
from collections import defaultdict


PER_CHAN_TIMEOUT = 60 # in seconds
USER_CTX_TIMEOUT = 180 # in seconds

COMMAND_REGEX = re.compile(r'([^"].*?|".*?")(?:\s|$)')

LOGGER = logging.getLogger(__name__)


class VoiceActivity(discord.Client):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subs = defaultdict(set)
        self._timeouts = set()
        self._users_context = dict()
        self._cmds = {
            cmd.name(): cmd(self) for cmd in commands.commands()
        }

    async def on_message(self, message):
        LOGGER.debug("got new message: '%s' from '%s' guild is '%s'", message.content, message.author.name, message.guild)
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
            cmd = self._cmds.get(cmd, self._unknown_command)
            ctx = {"user": user, "guild": guild, "resp_chan": resp_chan}
            LOGGER.info("invoking command %s for user %s", cmd, user.name)
            await cmd(ctx, *args)
        except Exception as e:
            LOGGER.info("couldn't parse command %a", e)
            await user.send(str(e))

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
        await ctx["user"].send("Unknown command, maybe try `help`?")

    async def on_voice_state_update(self, mem, bef, after):
        channel_changed = bef.channel != after.channel
        LOGGER.debug("voice state changed for user %s channel changed %s", mem.name, channel_changed)
        if after.channel is None:
            LOGGER.debug("user %s left channel", mem.name)
            return
        if after.channel.id in self._timeouts:
            LOGGER.debug("channel %s is still timed out", after.channel.name)
            return
        if channel_changed and len(after.channel.members) == 1:
            LOGGER.info("%s just joined channel %s(%a)", mem.name, after.channel.name, after.channel.id)
            LOGGER.info("channel members %a", after.channel.members)
            self._timeouts.add(after.channel.id)
            for user in self._subs[after.channel.id]:
                LOGGER.info("notifying user %s", user.name)
                if user != mem:
                    await user.send(f"Activity started on {after.channel} by {mem.name}")
            asyncio.create_task(self._revoke_timeout(after.channel.id))

    async def _revoke_timeout(self, channel_id):
        await asyncio.sleep(PER_CHAN_TIMEOUT)
        LOGGER.debug("revoking timeout on channel %A", channel_id)
        self._timeouts.remove(channel_id)

    async def _remove_context(self, user_id):
        await asyncio.sleep(USER_CTX_TIMEOUT)
        LOGGER.debug("removing user %a context", user_id)
        del self._users_context[user_id]

def run_client(token):
    cli = VoiceActivity()
    cli.run(token)
