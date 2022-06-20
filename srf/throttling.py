"""
@Author:WangYuXiang
@E-mile:Hill@3io.cc
@CreateTime:2022/6/8-9:52
@DependencyLibrary:[...]
@MainFunction:None
@FileDoc: 
    throttling is python file
@ChangeHistory:
    datetime action why
    2022/6/8-9:52 [Create] throttling.py
"""
import time
from typing import Union, Any

from srf.cache.backends import cache as default_cache
from srf.exceptions import Throttled


class BaseThrottle:
    """
    Rate throttling of requests.
    """

    async def allow_request(self, request, view):
        """
        Return `True` if the request should be allowed, `False` otherwise.
        """
        raise NotImplementedError('.allow_request() must be overridden')

    async def get_ident(self, request):
        """
        Use HTTP_X_FORWARDED_FOR to get REMOTE_ADDR,
        or use request.ip if it doesn't exist.
        """
        xff = request.headers.get('HTTP_X_FORWARDED_FOR', None)
        remote_addr = request.ip
        return ''.join(xff.split()) if xff else remote_addr

    async def wait(self):
        """
        Optionally, return a recommended number of seconds to wait before
        the next request.
        """
        return None


class SimpleRateThrottle(BaseThrottle):
    """
    A simple cache implementation, that only requires `.get_cache_key()`
    to be overridden.
    The rate (requests / seconds) is set by a `rate` attribute on the Throttle
    class.  The attribute is a string of the form 'number_of_requests/period'.
    Period should be one of: ('s', 'sec', 'm', 'min', 'h', 'hour', 'd', 'day')
    Previous request information used for throttling is stored in the cache.
    """
    cache = default_cache
    timer = time.time
    cache_format = 'throttle_%(scope)s_%(ident)s'
    rate = '100/min'

    def __init__(self, rate=None):
        if rate is not None:
            self.rate = rate
        self.num_requests, self.duration = self.parse_rate(self.rate)

    async def get_cache_key(self, request, view):
        """
        Should return a unique cache-key which can be used for throttling.
        Must be overridden.
        May return `None` if the request should not be throttled.
        """
        return await self.get_ident(request)

    def parse_rate(self, rate) -> Union[tuple[None, None], tuple[int, Any]]:
        """
        Given the request rate string, return a two tuple of:
        <allowed number of requests>, <period of time in seconds>
        """
        if rate is None:
            return None, None
        num, period = rate.split('/')
        num_requests = int(num)
        duration = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[period[0]]
        return num_requests, duration

    async def allow_request(self, request, view):
        """
        Implement the check to see if the request should be throttled.
        On success calls `throttle_success`.
        On failure calls `throttle_failure`.
        """
        if self.rate is None:
            return True

        self.key = await self.get_cache_key(request, view)
        if self.key is None:
            return True

        self.history = await self.cache.get(self.key, [])
        self.now = self.timer()

        # Drop any requests from the history which have now passed the
        # throttle duration
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()
        if len(self.history) >= self.num_requests:
            msg = 'Too many requests. Please try again later, Expected available in {wait} second.'
            raise Throttled(message=msg.format(wait=await self.wait()))
        self.history.insert(0, self.now)
        await self.cache.set(self.key, self.history, self.duration)
        return True

    async def wait(self):
        """
        Returns the recommended next request time in seconds.
        """
        if self.history:
            remaining_duration = self.duration - (self.now - self.history[-1])
        else:
            remaining_duration = self.duration

        available_requests = self.num_requests - len(self.history) + 1
        if available_requests <= 0:
            return None

        return int(remaining_duration / float(available_requests))
