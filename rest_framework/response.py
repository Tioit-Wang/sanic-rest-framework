"""
@Author:TioitWang
@E-mile:me@tioit.cc
@CreateTime:2022/6/6-10:53
@DependencyLibrary:[...]
@MainFunction:None
@FileDoc:
    response is python file
@ChangeHistory:
    datetime action why
    2022/6/6-10:53 [Create] response.py
"""
import datetime
import decimal
from typing import Dict, Optional, Union

import orjson
from sanic.compat import Header
from sanic.response import BaseHTTPResponse


def _default(obj):
    if isinstance(obj, datetime.datetime):
        if obj != obj:
            return None
        return int(obj.timestamp())
    elif isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, decimal.Decimal):
        return float(obj)
    elif hasattr(obj, "asdict"):
        return obj.asdict()
    elif hasattr(obj, "_asdict"):  # namedtuple
        return obj._asdict()
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    else:
        raise TypeError(f"Unsupported json dump type: {type(obj)}")


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
            dumps = orjson.dumps
        if body is None:
            body = {}
        self.content_type: Optional[str] = content_type
        option = orjson.OPT_PASSTHROUGH_DATETIME | orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_INDENT_2
        self.body = self._encode_body(dumps(body, default=_default, option=option))
        self.status = status
        self.headers = Header(headers or {})
        self._cookies = None

    async def eof(self):
        await self.send("", True)

    async def __aenter__(self):
        return self.send

    async def __aexit__(self, *_):
        await self.eof()
