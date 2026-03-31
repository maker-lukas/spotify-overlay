import asyncio
from dbus_next.aio import MessageBus
from dbus_next import Variant

SPOTIFY_BUS_NAME = "org.mpris.MediaPlayer2.spotify"
MPRIS_PATH = "/org/mpris/MediaPlayer2"
PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"

class SpotifyDBus:
    def __init__(self):
        self.bus = None
        self.player = None
        self.properties = None

    async def connect(self):
        self.bus = await MessageBus().connect()
        introspection = await self.bus.introspect(SPOTIFY_BUS_NAME, MPRIS_PATH)
        proxy = self.bus.get_proxy_object(SPOTIFY_BUS_NAME, MPRIS_PATH, introspection)
        self.player = proxy.get_interface(PLAYER_INTERFACE)
        self.properties = proxy.get_interface(PROPERTIES_INTERFACE)

    async def play_pause(self):
        await self.player.call_play_pause()

    async def next_track(self):
        await self.player.call_next()

    async def previous_track(self):
        await self.player.call_previous()

    async def open_uri(self, uri):
        await self.player.call_open_uri(uri)

    async def get_metadata(self):
        metadata = await self.properties.call_get(PLAYER_INTERFACE, "Metadata")
        data = metadata.value

        return {
            "title": str(data.get("xesam:title", Variant("s", "Unknown")).value),
            "artist": ", ".join(data.get("xesam:artist", Variant("as", ["Unknown"])).value),
            "album": str(data.get("xesam:album", Variant("s", "Unknown")).value),
            "art_url": str(data.get("mpris:artUrl", Variant("s", "")).value),
            "track_id": str(data.get("mpris:trackid", Variant("s", "")).value),
            "length": data.get("mpris:length", Variant("x", 0)).value,
        }

    async def get_playback_status(self):
        status = await self.properties.call_get(PLAYER_INTERFACE, "PlaybackStatus")
        return str(status.value)

    async def get_position(self):
        position = await self.properties.call_get(PLAYER_INTERFACE, "Position")
        return position.value

    async def get_shuffle(self):
        shuffle = await self.properties.call_get(PLAYER_INTERFACE, "Shuffle")
        return shuffle.value

    async def set_shuffle(self, enabled):
        await self.properties.call_set(PLAYER_INTERFACE, "Shuffle", Variant("b", enabled))

    async def get_loop_status(self):
        loop = await self.properties.call_get(PLAYER_INTERFACE, "LoopStatus")
        return str(loop.value)

    async def set_loop_status(self, status):
        await self.properties.call_set(PLAYER_INTERFACE, "LoopStatus", Variant("s", status))

    async def set_position(self, track_id, position_microseconds):
        await self.player.call_set_position(track_id, position_microseconds)

    async def seek(self, offset_microseconds):
        await self.player.call_seek(offset_microseconds)