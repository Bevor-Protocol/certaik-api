import asyncio
import datetime
import logging

from apscheduler.events import (
    EVENT_JOB_ADDED,
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    JobEvent,
    JobExecutionEvent,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.utils.enums import PlatformEnum
from app.web3.provider import get_provider

from .queues import queue_low

logging.basicConfig(level=logging.INFO)


scheduler = AsyncIOScheduler()


def schedule_submited_callback(event: JobEvent):
    pass
    # logging.info(f"event with job id {event.job_id} submitted")


def schedule_executed_callback(event: JobExecutionEvent):
    pass
    # if event.exception:
    #     logging.info(f"event with job id {event.job_id} failed {event.traceback}")
    # else:
    #     logging.info(f"event with job id {event.job_id} completed")


async def get_deployment_contracts():
    provider = get_provider(PlatformEnum.ETH)

    current_block = provider.eth.get_block_number()
    logging.info(f"Current block: {current_block}")
    receipts = provider.eth.get_block_receipts(current_block)

    deployment_addresses = []
    for receipt in receipts:
        if not receipt["to"]:
            logs = receipt["logs"]
            if logs:
                initial_log = logs[0]
                address = initial_log["address"]
                deployment_addresses.append(address)

    if deployment_addresses:
        logging.info(f"deployment addresses detected {','.join(deployment_addresses)}")
    else:
        logging.info("no deployment addresses found")


def enqueue_job(func, *args, **kwargs):
    # Enqueue job in Redis Queues
    queue_low.enqueue(func, *args, **kwargs)


async def my_simple_task():
    print("I started", datetime.datetime.now())
    await asyncio.sleep(3)
    print("I finished", datetime.datetime.now())


async def my_other_simple_task():
    print("I'm the other job", datetime.datetime.now())


every_minute = CronTrigger.from_crontab("*/1 * * * *")

scheduler.add_listener(schedule_submited_callback, EVENT_JOB_ADDED)
scheduler.add_listener(schedule_executed_callback, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)


# scheduler.add_job(enqueue_job, trigger=every_minute, args=[my_simple_task])
# scheduler.add_job(enqueue_job, trigger=every_minute, args=[my_other_simple_task])
scheduler.add_job(enqueue_job, trigger=every_minute, args=[get_deployment_contracts])
