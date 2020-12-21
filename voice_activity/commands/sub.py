from voice_activity.commands.abc import AbstractCommand

class SubCommand(AbstractCommand):

    @classmethod
    def name(cls) -> str:
        return "sub"

    async def run(self, ctx, chan):
        user, guild, resp_chan = ctx['user'], ctx['guild'], ctx['resp_chan']
        chan_name = chan
        try:
            [chan] = [ch for ch in guild.voice_channels if ch.name == chan_name]
        except ValueError:
            raise ValueError(f"channel {chan_name} doesn't exist")
        self._bot._subs[chan.id].add(user)
        await resp_chan.send(f"subscribed you to channel {chan.name}")


class UnsubCommand(AbstractCommand):

    @classmethod
    def name(cls) -> str:
        return "unsub"

    async def run(self, ctx, chan):
        user, guild, resp_chan = ctx['user'], ctx['guild'], ctx['resp_chan']
        try:
            [chan] = [ch for ch in guild.voice_channels if ch.name == chan]
        except ValueError:
            raise ValueError(f"channel {chan} doesn't exist")
        self._bot._subs[chan.id].remove(user)
        await resp_chan.send(f"unsubscribed you from channel {chan.name}")