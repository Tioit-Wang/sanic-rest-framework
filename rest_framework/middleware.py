from sanic import Sanic


class BaseMiddleware:

    def __init__(self, sanic_app: Sanic):
        self._sanic_app = sanic_app
        sanic_app.register_middleware(self.handle_request, "request")
        sanic_app.register_middleware(self.handle_response, "response")

    async def handle_request(self, request):
        pass

    async def handle_response(self, request, response):
        pass
