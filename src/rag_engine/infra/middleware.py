from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


class BodyLimitMiddleware:
    """Bound even chunked JSON input before FastAPI deserializes it."""

    def __init__(self, app: ASGIApp, max_bytes: int = 16384):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                response = JSONResponse(
                    {"error": {"code": "request_size", "message": "JSON body limit is 16 KiB."}},
                    status_code=413,
                )
                await response(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
