import asyncio
from spotify_dbus import SpotifyDBus

async def main():
    spotify = SpotifyDBus()
    await spotify.connect()
    await spotify.get_raw_metadata()

asyncio.run(main())