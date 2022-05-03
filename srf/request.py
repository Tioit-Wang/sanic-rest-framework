"""
@Author：WangYuXiang
@E-mile：Hill@3io.cc
@CreateTime：2021/3/11 15:46
@DependencyLibrary：无
@MainFunction：无
@FileDoc： 
    request.py
    文件说明
@ChangeHistory:
    datetime action why
    example:
    2021/3/11 15:46 change 'Fix bug'
        
"""

from sanic.exceptions import InvalidUsage
from sanic.request import Request as SanicRequest


class SRFRequest(SanicRequest):
    def __init__(self, *args, **kwargs):
        super(SRFRequest, self).__init__(*args, **kwargs)
        self.user = None

    @property
    def data(self):
        try:
            data = self.json
        except InvalidUsage as exc:
            data = self.form
        data = {} if data is None else data
        return data
