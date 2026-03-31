import asyncio
from spotify_dbus import SpotifyDBus

async def main():
    spotify = SpotifyDBus()
    await spotify.connect()

    meta = await spotify.get_metadata()
    print(f"Now playing: {meta['title']} by {meta['artist']}")

    status = await spotify.get_playback_status()
    print(f"Status: {status}")

asyncio.run(main())