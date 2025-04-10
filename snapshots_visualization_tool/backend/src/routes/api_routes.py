# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari

from fastapi import FastAPI

from . import _API_DATABASE


class API_ROUTES:
    def __init__(self, app: FastAPI) -> None:
        _API_DATABASE(app)
