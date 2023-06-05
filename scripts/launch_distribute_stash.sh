#!/bin/sh

env $(cat .env | xargs) poetry run python src/main.py distribute_stash
