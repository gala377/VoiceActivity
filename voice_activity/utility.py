def unapply_ctx(ctx):
    user, guild, resp_chan = ctx['user'], ctx['guild'], ctx['resp_chan']
    return user, guild, resp_chan


def get_voice_channel(guild, name):
    try:
        [chan] = [ch for ch in guild.voice_channels if ch.name == name]
    except ValueError:
        raise ValueError(f"channel {chan_name} doesn't exist")
    return chan
