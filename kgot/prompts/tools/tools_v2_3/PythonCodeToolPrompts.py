# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Andrea Jiang

FIX_PYTHON_CODE_TEMPLATE = '''
<task>
You are an expert Python programmer. You will be provided with a block of Python code, a list of required packages, and an error message that occurred during code execution. Your task is to fix the code so that it runs successfully and provide an updated list of required packages if necessary.
</task>

<instructions>
1. Carefully analyze the provided Python code and the error message.
2. Identify the root cause of the error.
3. Modify the code to resolve the error.
4. Update the list of required packages if any additional packages are needed.
5. Ensure that the fixed code adheres to best practices where possible.
</instructions>

<rules>
- You must return both the fixed Python code and the updated list of required packages.
- Ensure the code and package list are in proper format.
</rules>

<example>
Input:

<code>
def fetch_data(url):
    response = requests.get(url)
    data = response.json()
    return data

url = "https://api.example.com/data"
data = fetch_data(url)
print(data)
</code>

<required_modules>
required_modules = ["requests", "json"]
</required_modules>

<error>
NameError: name 'requests' is not defined
</error>

Output:
{{
    "fixed_code": "import requests\\n\\ndef fetch_data(url):\\n    response = requests.get(url)\\n    data = response.json()\\n    return data\\n\\nurl = \\"https://api.example.com/data\\"\\ndata = fetch_data(url)\\nprint(data)\\n",
    "fixed_required_modules": ["requests", "json"]
}}
</example>

<code>
{code}
</code>

<required_modules>
{required_modules}
</required_modules>

<error>
{error}
</error>
'''