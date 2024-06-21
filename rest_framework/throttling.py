"""
@Author:TioitWang
@E-mile:me@tioit.cc
@CreateTime:2022/6/8-9:52
@DependencyLibrary:[...]
@MainFunction:None
@FileDoc:
    throttling is python file
@ChangeHistory:
    datetime action why
    2022/6/8-9:52 [Create] throttling.py
"""

import json
import time
from typing import Union, Any

from rest_framework.exceptions import ThrottledException
from rest_framework.cache.backends.base import cache_manager


class BaseThrottle:
    """
    Rate throttling of requests.
    """

    cache_format = 'throttle_%s'
    rate = '50/min'

    def __init__(self, rate=None, cache_engine_name='default'):
        """
        Initializes the BaseThrottle class.

        Args:
            rate (str, optional): Rate limit as a string, e.g., '50/min'. Defaults to None.
        """
        if rate is not None:
            self.rate = rate
        self.num_requests, self.duration = self.parse_rate(self.rate)
        self.cache_engine = cache_manager.get_cache(cache_engine_name)

    def parse_rate(self, rate) -> Union[tuple[None, None], tuple[int, Any]]:
        """
        Parses the rate string into number of requests and duration.

        Args:
            rate (str): Rate limit as a string, e.g., '50/min'.

        Returns:
            tuple: Number of requests and duration in milliseconds.
        """
        if rate is None:
            return None, None
        try:
            num, period = rate.split('/')
            num_requests = int(num)
            duration = {'s': 1000, 'm': 60000, 'h': 3600000, 'd': 86400000}.get(period[0])
            if duration is None:
                raise ValueError("Unsupported rate period.")
            return num_requests, duration
        except ValueError as e:
            raise ValueError(f"Invalid rate format: {rate}. Error: {str(e)}")

    async def allow_request(self, request):
        """
        Return `True` if the request should be allowed, `False` otherwise.
        """
        raise NotImplementedError('.allow_request() must be overridden')

    async def get_ident(self, request):
        """
        Use x-real-ip to get REMOTE_ADDR, or use request.ip if it doesn't exist.

        Returns:
            str: The identifier for the given request.
        """
        xff = request.headers.get('x-real-ip', None)
        remote_addr = request.ip

        return ''.join(xff.split()) if xff else remote_addr

    async def wait(self):
        """
        Optionally, return a recommended number of seconds to wait before the next request.
        """
        return None


class RedisThrottle(BaseThrottle):
    """
    Redis-based request throttling.
    """

    cache_format = 'throttle_%s'
    rate = '50/min'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history = []

    async def allow_request(self, request, view):
        """
        Check if the request should be throttled.

        Args:
            request: The incoming request object.
            view: The view handling the request.

        Returns:
            bool: `True` if the request is allowed, `False` otherwise.

        Raises:
            ThrottledException: If the request is throttled.
        """
        if self.rate is None:
            return True

        ident = await self.get_ident(request)
        cache_key = self.cache_format % ident

        cache_value = await self.cache_engine.get(cache_key)
        if cache_value is not None:
            self.history = json.loads(cache_value)

        self.now = int(time.time() * 1000)  # in milliseconds

        # Drop any requests from the history which have now passed the throttle duration
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()

        if len(self.history) >= self.num_requests:
            msg = 'Too many requests. Please try again later, Expected available in {wait} second.'
            raise ThrottledException(message=msg.format(wait=await self.wait()))

        self.history.insert(0, self.now)
        await self.cache_engine.set(cache_key, json.dumps(self.history), timeout=self.duration)
        return True

    async def wait(self):
        """
        Returns the recommended next request time in seconds.

        Returns:
            int: Number of seconds to wait.
        """
        if self.history:
            remaining_duration = self.duration - (self.now - self.history[-1])
        else:
            remaining_duration = self.duration

        available_requests = self.num_requests - len(self.history) + 1
        if available_requests <= 0:
            return None

        return int(remaining_duration / float(available_requests) / 1000)
