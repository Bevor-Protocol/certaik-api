from rq import Queue

from .cache import redis_client

queue_high = Queue("high", connection=redis_client)
queue_low = Queue("low", connection=redis_client)
