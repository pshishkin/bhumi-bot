#!/bin/sh

env $(cat .env | xargs) poetry run python src/discord_payment.py
