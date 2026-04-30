#!/usr/bin/env python3
"""Simple test script to dump all Spotify DBus data to the terminal."""
import asyncio
from dbus_next.aio import MessageBus
from dbus_next import Variant

SPOTIFY_BUS_NAME = "org.mpris.MediaPlayer2.spotify"
MPRIS_PATH = "/org/mpris/MediaPlayer2"
ROOT_INTERFACE = "org.mpris.MediaPlayer2"
PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"


def unwrap(value):
    """Recursively unwrap dbus_next Variant values for clean printing."""
    if isinstance(value, Variant):
        return unwrap(value.value)
    if isinstance(value, dict):
        return {k: unwrap(v) for k, v in value.items()}
    if isinstance(value, list):
        return [unwrap(v) for v in value]
    return value


def print_section(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def main():
    try:
        bus = await MessageBus().connect()
    except Exception as e:
        print(f"Failed to connect to session bus: {e}")
        return

    try:
        introspection = await bus.introspect(SPOTIFY_BUS_NAME, MPRIS_PATH)
    except Exception as e:
        print(f"Failed to introspect Spotify on DBus.")
        print(f"Is Spotify running? Error: {e}")
        return

    proxy = bus.get_proxy_object(SPOTIFY_BUS_NAME, MPRIS_PATH, introspection)
    properties = proxy.get_interface(PROPERTIES_INTERFACE)

    print_section("Root interface (org.mpris.MediaPlayer2)")
    try:
        root_props = await properties.call_get_all(ROOT_INTERFACE)
        for key, variant in root_props.items():
            print(f"  {key}: {unwrap(variant)}")
    except Exception as e:
        print(f"  error: {e}")

    print_section("Player interface (org.mpris.MediaPlayer2.Player)")
    try:
        player_props = await properties.call_get_all(PLAYER_INTERFACE)
        for key, variant in player_props.items():
            if key == "Metadata":
                continue
            print(f"  {key}: {unwrap(variant)}")
    except Exception as e:
        print(f"  error: {e}")

    print_section("Metadata (xesam:* / mpris:*)")
    try:
        metadata_variant = await properties.call_get(PLAYER_INTERFACE, "Metadata")
        metadata = metadata_variant.value
        for key, variant in metadata.items():
            print(f"  {key}: {unwrap(variant)}")
    except Exception as e:
        print(f"  error: {e}")

    print_section("Convenient summary")
    try:
        metadata_variant = await properties.call_get(PLAYER_INTERFACE, "Metadata")
        data = metadata_variant.value
        title = data.get("xesam:title", Variant("s", "Unknown")).value
        artist = ", ".join(data.get("xesam:artist", Variant("as", ["Unknown"])).value)
        album = data.get("xesam:album", Variant("s", "Unknown")).value
        art_url = data.get("mpris:artUrl", Variant("s", "")).value
        track_id = data.get("mpris:trackid", Variant("s", "")).value
        length = data.get("mpris:length", Variant("x", 0)).value
        url = data.get("xesam:url", Variant("s", "")).value

        status = (await properties.call_get(PLAYER_INTERFACE, "PlaybackStatus")).value
        position = (await properties.call_get(PLAYER_INTERFACE, "Position")).value

        print(f"  Title:       {title}")
        print(f"  Artist:      {artist}")
        print(f"  Album:       {album}")
        print(f"  Art URL:     {art_url}")
        print(f"  Track ID:    {track_id}")
        print(f"  Spotify URL: {url}")
        print(f"  Length:      {length} µs ({length / 1_000_000:.2f} s)")
        print(f"  Position:    {position} µs ({position / 1_000_000:.2f} s)")
        print(f"  Status:      {status}")
    except Exception as e:
        print(f"  error: {e}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
