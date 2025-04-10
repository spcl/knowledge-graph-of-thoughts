# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari
#               Andrea Jiang

import logging
from pprint import pformat
from typing import Any, List, Optional, Tuple, Type

import requests
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from kgot.prompts.tools.tools_v2_3 import FIX_PYTHON_CODE_TEMPLATE
from kgot.utils import UsageStatistics, llm_utils
from kgot.utils.log_and_statistics import collect_stats

logger = logging.getLogger("Controller.PythonCodeTool")


class RunPythonCodeSchema(BaseModel):
    code: str = Field(description="The Python code to be executed. **ALWAYS** add a print statement for the final answer")
    required_modules: Optional[List[str]] = Field(default=[], description="Optional list of required modules to be installed before execution. (e.g. ['numpy', 'pandas'])")


class RunPythonCodeTool(BaseTool):
    name: str = "Python_Code_Executor"
    description: str = """
This tool executes Python code. Users can specify the code and any required packages. Best tool for math and statistic computations.
**ALWAYS** add a print statement for the final answer

## Usage Examples:
1. **Basic Execution** (No additional packages):
code = '''print('Hello, World!')'''
response = tool._run(code)
# Expected output: {"output": "Hello, World!"}

1. **With Required Packages**:
code = '''import numpy as np\n print(np.zeros(5))'''
required_modules = ["numpy"]
response = tool._run(code, required_modules)
# Expected output: {"output": "[0. 0. 0. 0. 0.]"}

Limitations:
- Execution Environment: Python 3.9. Some packages may not be supported or installable.
- File Access: Direct file access is not allowed. If your code needs to work with files, they must be accessible via a URL.
"""
    args_schema: Type[BaseModel] = RunPythonCodeSchema
    llm: Type[Runnable] = None
    url: str = None
    try_to_fix: bool = None
    times_to_fix: int = None
    usage_statistics: UsageStatistics = None

    # Note, that IF try_to_fix is True, you will need to set the model_name and temperature
    def __init__(
            self,
            model_name: str = "", 
            temperature: float = 0.0, 
            try_to_fix: bool = False, 
            times_to_fix: int = 3, 
            python_executor_uri: str = "http://localhost:16000/run",
            usage_statistics: UsageStatistics = None, 
            **kwargs: Any):
        
        super().__init__(**kwargs)

        self.try_to_fix = try_to_fix
        self.url = python_executor_uri
        if self.try_to_fix:
            self.times_to_fix = times_to_fix
            # Check if the model and temperature are set
            if not model_name:
                raise ValueError("If try_to_fix is True, the model_name and temperature must be set. model_name: {}, temperature: {}".format(model_name, temperature))
            self.llm = llm_utils.get_llm(model_name=model_name, temperature=temperature)

            self.usage_statistics = usage_statistics

    @collect_stats("RunPythonCodeTool._fix_code")
    def _fix_code(self, error: str, code: str, required_modules: Optional[List[str]] = None) -> Tuple[str, Optional[List[str]]]:
        class FixedCode(BaseModel):
            fixed_code: str = Field(description="The fixed code")
            fixed_required_modules: Optional[List[str]] = Field(description="The fixed list of required modules")

        prompt_template = PromptTemplate(
            input_variables=["code",
                             "required_modules",
                             "error"],
            template=FIX_PYTHON_CODE_TEMPLATE,
        )

        completed_prompt = prompt_template.invoke({"code": code,
                                                   "required_modules": required_modules,
                                                   "error": error})
        logger.info(f"Prompt template of _fix_code: {completed_prompt.text}")

        chain = self.llm.with_structured_output(FixedCode, method="json_schema")
        response = chain.invoke(completed_prompt)
            
        logger.info(f"New code and list of requirements:\n{pformat(response, width=160)}")

        fixed_code = response.fixed_code
        fixed_required_modules = response.fixed_required_modules
        return fixed_code, fixed_required_modules

    def _run(self, code: str, required_modules: Optional[List[str]] = None) -> Any:
        try:
            response = requests.post(self.url, json={"code": code, "required_modules": required_modules})
            text = response.text

            # Try to fix the code if it fails and possible
            while not response.ok and self.try_to_fix and self.times_to_fix > 0:
                self.times_to_fix -= 1

                logger.error(f"Error in code execution: {text}. Attempts to fix left: {self.times_to_fix}")
                try:
                    code, required_modules = self._fix_code(text, code, required_modules)
                except Exception as e:
                    logger.error(f"Error in fixing the code: {str(e)}")
                    break

                response = requests.post(self.url, json={"code": code, "required_modules": required_modules})
                text = response.text

            if response.ok:
                return response.json()
            else:
                return {"error": text}
        except Exception as e:
            logger.error(f"Error in _run method: {str(e)}")
            return {"error": str(e)}
