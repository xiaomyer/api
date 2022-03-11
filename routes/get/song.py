import itertools

from aiohttp import web
from bs4 import BeautifulSoup
from dotenv import dotenv_values

config = dotenv_values()

def cache(function: function) -> function:
    _cache = {}
    async def inner(request: web.Request):
        if not "artist" in request.query or not "song" in request.query:
            raise web.HTTPBadRequest(text="\"artist\" and \"song\" are required parameters that are missing")
        if _cache.get((request.query.get("artist"), request.query.get("song"))) is not None:
            return _cache.get((request.query.get("artist"), request.query.get("song")))
        else:
            response: web.Response = await function(request)
            _cache[(request.query.get("artist"), request.query.get("song"))] = response
            return response
    return inner

@cache
async def song(request: web.Request) -> web.Response:
    song: dict = await _get_song_info(request.app["client"], request.query.get("artist"), request.query.get("song"))
    if not song:
        raise web.HTTPNotFound(text="Song not found")
    lyrics: list = await _scrape_lyrics(request.app["client"], song.get("url"))
    return web.json_response({
        "artists": song.get("artist_names"),
        "title": song.get("title"),
        "full_title": song.get("full_title"),
        "lyrics": lyrics
    })

async def _get_song_info(_client, artist, song) -> dict:
    async with _client.get("https://api.genius.com/search", params={"q": f"{artist} - {song}"}, headers={"Authorization": f"Bearer {config['GENIUS_CLIENT_ACCESS_TOKEN']}"}) as response:
        json: dict = await response.json()
        if not bool(json.get("response", {}).get("hits")): return
        song: dict = json.get("response", {}).get("hits")[0].get("result")
        return song

async def _scrape_lyrics(_client, url) -> list:
    async with _client.get(url) as response:
        html: BeautifulSoup = BeautifulSoup(await response.text(), "html.parser")
        lyrics: list = list(itertools.chain.from_iterable(list(tag.stripped_strings) for tag in html.find_all(attrs={"data-lyrics-container": "true"})))
        return lyrics

def setup(app: web.Application):
    app.add_routes([web.get("/song", song)])