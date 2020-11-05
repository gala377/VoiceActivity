import discord
import asyncio
import re
import commands

from collections import defaultdict


PER_CHAN_TIMEOUT = 60 # in seconds
USER_CTX_TIMEOUT = 180 # in seconds

COMMAND_REGEX = re.compile(r'([^"].*?|".*?")(?:\s|$)')

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
        if message.author == self.user:
            return
        elif message.guild is not None and self.user in message.mentions:
            await self._in_chan_callout(message)
        elif message.guild is None:
            ctx = self._users_context.get(message.author.id)
            if ctx is None:
                await message.author.send(
                    "sorry, could you call me from the server you want to execute commands in.")
            else:
                await self._run_cmd(message.author, ctx.guild, message.content)

    async def _in_chan_callout(self, message):
        reply = message.author
        if reply.id not in self._users_context:
            self._users_context[reply.id] = reply
            asyncio.create_task(self._remove_context(reply.id))
        await reply.send("What do you want from me?")

    async def _run_cmd(self, user, guild, content):
        try:
            cmd, args = self._parse_cmd(content)
            cmd = self._cmds.get(cmd, self._unknown_command)
            ctx = {"user": user, "guild": guild}
            await cmd(ctx, *args)
        except Exception as e:
            await user.send(str(e))

    def _parse_cmd(self, mess):
        """
        Here we should parse command and its arguments.
        If anything is wrong (for example number of arguments
        for the command does not match) then exception should
        be raised.
        """
        try:
            matches = COMMAND_REGEX.findall(mess)
            matches = [x.strip('"') for x in matches]
            cmd, *args = matches
        except ValueError:
            raise ValueError("wrong command format, expected `cmd arg2 arg2...`")
        return cmd, args

    async def _unknown_command(self, ctx, *args):
        await ctx["user"].send("Unknown command, maybe try `help`?")

    async def on_voice_state_update(self, mem, bef, after):
        channel_changed = bef.channel != after.channel
        if after.channel is None:
            return
        if after.channel.id in self._timeouts:
            return
        if channel_changed and len(after.channel.members) == 1:
            self._timeouts.add(after.channel.id)
            for user in self._subs[after.channel.id]:
                if user != mem:
                    await user.send(f"Activity started on {after.channel} by {mem.name}")
            asyncio.create_task(self._revoke_timeout(after.channel.id))

    async def _revoke_timeout(self, channel_id):
        await asyncio.sleep(PER_CHAN_TIMEOUT)
        self._timeouts.remove(channel_id)

    async def _remove_context(self, user_id):
        await asyncio.sleep(USER_CTX_TIMEOUT)
        del self._users_context[user_id]

def run_client(token):
    cli = VoiceActivity()
    cli.run(token)
