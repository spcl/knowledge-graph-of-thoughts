# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari

from kgot.tools.PythonCodeTool import RunPythonCodeTool
from kgot.tools.tool_manager_interface import ToolManagerInterface
from kgot.tools.tools_v2_3.ExtractZipTool import ExtractZipTool
from kgot.tools.tools_v2_3.ImageQuestionTool import ImageQuestionTool
from kgot.tools.tools_v2_3.LLMTool import LangchainLLMTool
from kgot.tools.tools_v2_3.SurferTool import SearchTool
from kgot.tools.tools_v2_3.TextInspectorTool import TextInspectorTool
from kgot.tools.tools_v2_3.Web_surfer import init_browser
from kgot.utils import UsageStatistics


class ToolManager(ToolManagerInterface):
    """
    ToolManager v2.3 class for managing tools.
    Inherits from ToolManagerInterface.

    Attributes:
        usage_statistics (UsageStatistics): Usage statistics for the tools
        config_path (str): Path to the configuration file
        tools (list[BaseTool]): List of tools
    """

    def __init__(
        self,
        usage_statistics: UsageStatistics,
        base_config_path: str = "kgot/config_tools.json",
        additional_config_path: str = "kgot/tools/tools_v2_3/additional_config_tools.json",
        python_executor_uri: str = "http://localhost:16000",
    ) -> None:
        """
        Initialize the ToolManager.

        Args:
            usage_statistics (UsageStatistics): Usage statistics for the tools
            base_config_path (str): Path to the configuration file
            additional_config_path (str): Path to the additional configuration file
            python_executor_uri (str): URI for the Python Docker service
        """
        super().__init__(usage_statistics, base_config_path, additional_config_path)

        init_browser()
        ### TOOLS ###
        extract_zip_tool = ExtractZipTool()
        search_tool = SearchTool(model_name="gpt-4o-mini", temperature=0.5, usage_statistics=usage_statistics)
        LLM_tool = LangchainLLMTool(model_name="gpt-4o-mini", temperature=0.5, usage_statistics=usage_statistics)
        textInspectorTool = TextInspectorTool(model_name="gpt-4o-mini", temperature=0.5, usage_statistics=usage_statistics)
        image_question_tool = ImageQuestionTool(model_name="gpt-4o-mini", temperature=0.5, usage_statistics=usage_statistics) 
        run_python_tool = RunPythonCodeTool(
            try_to_fix=True,
            times_to_fix=3,
            model_name="gpt-4o-mini",
            temperature=0.5,
            python_executor_uri=python_executor_uri,
            usage_statistics=usage_statistics,
        )
        
        self.tools.extend([
            LLM_tool,
            image_question_tool,
            textInspectorTool,
            search_tool,
            run_python_tool,
            extract_zip_tool,
        ])
            
        # Test for python docker
        self._test_python_docker(run_python_tool)

    def _test_python_docker(self, python_tool: RunPythonCodeTool) -> None:
        """
        Test the Python Docker service by running a simple code snippet.
        If the service is not running, an exception is raised.

        Args:
            python_executor_uri (str): URI for the Python Docker service
        """
        response = python_tool._run("""
import os
print("Hello, World!")
print("Python Docker service is running.")
""")
        
        if response.get("error"):
            print(
                "\n\n\033[1;31m" + "Failed to connect to Docker instance! Be sure to have a running Docker instance and double check the connection parameters.\n\n")
            exit(1)


if __name__ == "__main__":
    tool_manager = ToolManager(None, additional_config_path="kgot/tools/tools_v2_3/additional_config_tools.json")
    print(tool_manager.get_tools())
