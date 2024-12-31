import os

from redis import Redis

redis_client = Redis(host=os.getenv("REDIS_HOST"), port=6379)
