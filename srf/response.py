"""
@Author:WangYuXiang
@E-mile:Hill@3io.cc
@CreateTime:2022/6/6-10:53
@DependencyLibrary:[...]
@MainFunction:None
@FileDoc: 
    response is python file
@ChangeHistory:
    datetime action why
    2022/6/6-10:53 [Create] response.py
"""
from typing import Optional, Union, Dict

from sanic.compat import Header
from sanic.response import BaseHTTPResponse


class JsonResponse(BaseHTTPResponse):
    __slots__ = ("body", "status", "content_type", "headers", "_cookies")

    def __init__(
            self,
            body: dict = None,
            status: int = 200,
            headers: Optional[Union[Header, Dict[str, str]]] = None,
            content_type: Optional[str] = "application/json",
            dumps=None
    ):
        super().__init__()
        if not dumps:
            dumps = BaseHTTPResponse._dumps
        if body is None:
            body = {}
        self.content_type: Optional[str] = content_type
        self.body = self._encode_body(dumps(body))
        self.status = status
        self.headers = Header(headers or {})
        self._cookies = None

    async def eof(self):
        await self.send("", True)

    async def __aenter__(self):
        return self.send

    async def __aexit__(self, *_):
        await self.eof()
