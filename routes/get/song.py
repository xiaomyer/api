import itertools

from aiohttp import web
from bs4 import BeautifulSoup
from dotenv import dotenv_values

config = dotenv_values()
cache = {}

async def song(request):
    if not "artist" in request.query or not "song" in request.query:
        raise web.HTTPBadRequest(text="Missing parameters: \"artist\" and \"song\" are required")
    song = cache.get((request.query.get("artist"), request.query.get("song"))) or await _get_song_info(request.app["client"], request.query.get("artist"), request.query.get("song"))
    if not song:
        raise web.HTTPBadRequest(text="Song not found")
    cache[(request.query.get("artist"), request.query.get("song"))] = song
    lyrics = await _scrape_lyrics(request.app["client"], song.get("url"))
    return web.json_response({
        "artists": song.get("artist_names"),
        "title": song.get("title"),
        "full_title": song.get("full_title"),
        "lyrics": lyrics
    })

async def _get_song_info(_client, artist, song):
    async with _client.get("https://api.genius.com/search", params={"q": f"{artist} - {song}"}, headers={"Authorization": f"Bearer {config['GENIUS_CLIENT_ACCESS_TOKEN']}"}) as response:
        json = await response.json()
        if not bool(json.get("response", {}).get("hits")): return
        song = json.get("response", {}).get("hits")[0].get("result")
        return song

async def _scrape_lyrics(_client, url):
    async with _client.get(url) as response:
        html = BeautifulSoup(await response.text(), "html.parser")
        lyrics = list(itertools.chain.from_iterable(list(tag.stripped_strings) for tag in html.find_all(attrs={"data-lyrics-container": "true"})))
        return lyrics

def setup(app):
    app.add_routes([web.get("/song", song)])