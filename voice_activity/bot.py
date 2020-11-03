import discord
import asyncio

from collections import defaultdict


PER_CHAN_TIMEOUT = 60 # in seconds
USER_CTX_TIMEOUT = 180 # in seconds

class VoiceActivityError(Exception): ...
class ParsingError(VoiceActivityError): ...
class CommandError(VoiceActivityError): ...


class VoiceActivity(discord.Client):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # chan id is globally unique so we do not have
        # to store guild id
        self._subs = defaultdict(set)
        self._timeouts = set()
        self._users_context = dict()
        self._cmds = {
            'sub': self._sub_command,
            'unsub': self._unsub_command,
            'help': self._help_command,
        }

    async def on_message(self, message):
        if message.author == self.user:
            return
        elif message.content == "ej staszek":
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
            await cmd(user, guild, *args)
        except VoiceActivityError as e:
            await user.send(str(e))
        except Exception as e:
            await user.send(f"Unexpected Error {str(e)}")

    def _parse_cmd(self, mess):
        """
        Here we should parse command and its arguments.
        If anything is wrong (for example number of arguments
        for the command does not match) then exception should
        be raised.
        """
        try:
            cmd, *args = mess.split(" ")
        except ValueError:
            raise ParsingError("wrong command format, expected `cmd arg2 arg2...`")
        return cmd, args

    async def _sub_command(self, user, guild, chan):
        try:
            [chan] = [ch for ch in guild.voice_channels if ch.name == chan]
        except ValueError:
            raise CommandError("channel doesn't exist")
        self._subs[chan.id].add(user)
        await user.send(f"subscribed you to channel {chan.name}")

    async def _unsub_command(self, user, guild, chan):
        try:
            [chan] = [ch for ch in guild.voice_channels if ch.name == chan]
        except ValueError:
            raise CommandError("channel doesn't exist")
        self._subs[chan.id].remove(user)
        await user.send(f"unsubscribed you from channel {chan.name}")

    async def _help_command(self, user, guild):
        await user.send("sub/unsub channel_name")

    async def _unknown_command(self, user, guild, *args):
        await user.send("Unknown command")
        await self._help_command(user, guild)

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
