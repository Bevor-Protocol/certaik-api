# Certaik API

To be used for interfacing with certaik application, and main function is for managing the GAME api integration with Virtuals.

## Getting started

Install `poetry`

`poetry install` will create your virtual environment

`docker compose up` will start the services

### Redis

Redis queue is used for background processing, and to enable cron tasks.

To observe the queue, `poetry shell` followed by `rq info`
