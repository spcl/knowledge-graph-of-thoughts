#!/bin/bash

# Load environment variables
set -a
source .env
set +a

PYTHON_APP_DIR=$(realpath ./files)

bash -c "
nohup sarus run \
 --workdir=/app \
 --env FLASK_APP=python_executor.py \
 --mount=type=bind,source=$PYTHON_APP_DIR,destination=/app \
 python:3.12-slim \
  bash -c \"pip3 install --no-cache-dir -r requirements.txt && waitress-serve --port=${PORT} python_executor:app\" \
   > sarus_python.log 2>&1 &
"