# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# authors: Andrea Jiang
#          Lorenzo Paleari
#          You Wu

import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError

import requests
from flask import Flask, jsonify, request
from langchain_experimental.utilities import PythonREPL

app = Flask(__name__)
PYTHON_EXECUTOR_HOST = 'localhost'
PYTHON_EXECUTOR_PORT = 16000

def is_standard_lib(package: str) -> bool:
    """
    Return whether the specified package is part of the standard library.

    :param package: Package name to check.
    :type package: str
    :return: True if the package is a standard library. False otherwise.
    :rtype: bool
    """
    return package in sys.stdlib_module_names

def install(package: str) -> None:
    """
    Install the specified Python package.

    :param package: Python package to install.
    :type package: str
    """
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

@app.route('/run', methods=['POST'])
def run_code() -> tuple[requests.Response, int]:
    """
    Install required packages, run Python code and return the output.

    The input JSON request should contain the following keys:
    - required_modules: list[str] - List of packages to install.
    - code: str - Python code to run.

    :return: Tuple of the response and the status code.
    :rtype: tuple[requests.Response, int]
    """
    timeout_seconds = 240

    required_modules = request.json.get('required_modules', [])
    print("Required modules:", required_modules)
    if required_modules:
        for module in required_modules:
            if is_standard_lib(module):
                print(f"'{module}' is a standard library module. Skipping installation.")
            else:
                install(module)

    code = request.json.get('code')
    if not code:
        return jsonify({"error": "No code provided"}), 400

    python_repl = PythonREPL()

    # Function to execute the code
    def execute_code() -> tuple[requests.Response, int]:
        """
        Execute code.

        :return: Tuple of the response and the status code.
        :rtype: tuple[requests.Response, int]
        """

        def is_error_string(s: str) -> bool:
            """
            Check whether the returned output is an error string.

            PythonREPL does not throw an error, so we need to use a regex to check if the code is
            valid.

            :param s: Returned output.
            :type s: str
            :return: True if returned output is an error string. False otherwise.
            :rtype: bool
            """

            # Regular expression for a common exception format
            error_pattern = re.compile(r'^[a-zA-Z_]+Error\((.*)\)$')  # TODO, check if this is the correct regex for all possible cases, for now catching e.g. "NameError(name 'x' is not defined)"
            matched = error_pattern.match(s)
            print("Matched:", matched)
            return bool(matched)

        result = python_repl.run(code)

        if is_error_string(result):
            return {"error": result}, 400
        else:
            return {"output": result}, 200

    # Use ThreadPoolExecutor to set a timeout for code execution
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(execute_code)

    try:
        result, status_code = future.result(timeout=timeout_seconds)  # Execute with a timeout of 240 seconds
    except TimeoutError:
        return jsonify({"error": "Code execution timed out"}), 408
    except Exception as e:
        return jsonify({"error": str(e)}), 400  # Catch any other error and return it

    # Properly return the result and status code
    return jsonify(result), status_code


if __name__ == '__main__':
    from waitress import serve

    serve(app, host=PYTHON_EXECUTOR_HOST, port=PYTHON_EXECUTOR_PORT)
