"""
@Author:TioitWang
@E-mile:me@tioit.cc
@CreateTime:2021/3/11 15:46
@DependencyLibrary:无
@MainFunction:无
@FileDoc:
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
        Warning(" .data is deprecated, please use .post_data, .data will be removed in V1.7")
        return self._build_data()

    @property
    def get_data(self):
        return self.args

    @property
    def post_data(self):
        return self._build_data()

    # def _build_args(self):
    #     args = self.args
    #     args = {} if args is None else args
    #     for i in args:
    #         if len(args[i]) == 1:
    #             args[i] = args[i][0]
    #         return args
    #     return args

    def _build_data(self):
        try:
            data = self.json
        except InvalidUsage as exc:
            data = self.form
        data = {} if data is None else data
        return data
