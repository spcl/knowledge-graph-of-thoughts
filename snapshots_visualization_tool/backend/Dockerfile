# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari

FROM python:3.11

# Add build arguments for UID and GID
ARG UID=1000
ARG GID=1000

# Create a group and user with the specified UID and GID
RUN groupadd -g ${GID} backend_py && \
    useradd -u ${UID} -g backend_py -m backend_py

WORKDIR /src

# Copy requirements and set ownership to the backend_py user
COPY --chown=backend_py:backend_py ./requirements.txt /requirements.txt

# Set environment variables
ARG API_PORT
ENV API_PORT=${API_PORT}
ARG NEO4J_INTERNAL_HOST
ENV NEO4J_INTERNAL_HOST=${NEO4J_INTERNAL_HOST}

# Install dependencies as root
RUN pip install --no-cache-dir --upgrade -r /requirements.txt

# Copy the rest of the application code and set ownership to the backend_py user
COPY --chown=backend_py:backend_py ./src/ /src/

# Switch to the backend_py user
USER backend_py

# Set the command to run the application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "443"]
