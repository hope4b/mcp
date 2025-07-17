from __future__ import annotations

class FastMCP:
    def __init__(self, name: str):
        self.name = name
        self._tools = {}
        self._resources = {}

    def tool(self, func):
        self._tools[func.__name__] = func
        return func

    def resource(self, name: str):
        def decorator(func):
            self._resources[name] = func
            return func
        return decorator

    def run(self):
        # Stub: does nothing
        pass

    def asgi_app(self):
        async def app(scope, receive, send):
            pass
        return app
