import json
import importlib
import os

from aiohttp import web, ClientSession

async def startup(app):
    app["client"] = ClientSession()

async def shutdown(app):
    await app["client"].close()

@web.middleware
async def wrapper(request, handler):
    try:
        response = await handler(request)
        return web.json_response({"success": True, "status": response.status, "data": json.loads(response.text)})
    except web.HTTPException as exception:
        return web.json_response({"success": False, "status": exception.status, "error": exception.text})

async def api():
    app = web.Application(middlewares=[wrapper])
    routes = [os.path.join(dp, f) for dp, _, fn in os.walk("routes") for f in fn]
    for route in routes:
        if "__pycache__" in route: continue
        module = importlib.import_module((route.replace("/", "."))[:-3])
        module.setup(app)
    app.on_startup.append(startup)
    app.on_shutdown.append(shutdown)
    return app
