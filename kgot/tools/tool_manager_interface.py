# Copyright (c) 2025 ETH Zurich.
#                    All rights reserved.
#
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Main authors: Lorenzo Paleari

import json
import os
from abc import ABC

from langchain_core.tools import BaseTool

from kgot.utils import UsageStatistics


class ToolManagerInterface(ABC):
    """
    Abstract class for ToolManager

    Attributes:
        usage_statistics (UsageStatistics): Usage statistics for the tools
        base_config_path (str): Path to the base configuration file
        tools (list[BaseTool]): List of tools
    """

    def __init__(self, usage_statistics: UsageStatistics, base_config_path: str = "kgot/config_tools.json", additional_config_path: str = None) -> None:
        """
        Initialize the ToolManagerInterface.

        Args:
            usage_statistics (UsageStatistics): Usage statistics for the tools
            base_config_path (str): Path to the base configuration file
            additional_config_path (str): Path to the additional configuration file
        """
        self.base_config_path = base_config_path
        self.additional_config_path = additional_config_path
        self.usage_statistics = usage_statistics
        self.tools: list[BaseTool] = []

        # Load the configuration file for tools
        self.set_env_keys(self.base_config_path, self.additional_config_path)

    @staticmethod
    def set_env_keys(base_config_path: str = "kgot/config_tools.json", additional_config_path: str = None) -> None:
        """
        Set environment variables for the tools based on the configuration file.
        """
        with open(base_config_path, 'r') as file:
            config = json.load(file)
            config_dict = {tool['name']: tool for tool in config}

        # Check if the additional config file exists
        if additional_config_path is not None:
            try:
                with open(additional_config_path, 'r') as file:
                    additional_config = json.load(file)

                # Merge the additional config with the base config
                for tool in additional_config:
                    if tool["name"] in config_dict:
                        config_dict[tool["name"]].update(tool)
                        continue 

                    config_dict[tool["name"]] = tool
            except FileNotFoundError:
                print(f"Additional config file {additional_config_path} not found. Skipping.")

        for tool_config in config_dict.values():
            if 'env' in tool_config:
                env_vars = tool_config['env']
                for key, value in env_vars.items():
                    os.environ[key] = value

    def get_tools(self) -> list[BaseTool]:
        """"
        Get the list of tools.
        """
        return self.tools