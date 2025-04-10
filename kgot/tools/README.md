# Integrated Tools

The **Integrated Tools Module** is a key part of our KGoT framework and enables the multi-modal reasoning capabilities of the framework, which allows KGoT to tackle a wide range of tasks ranging from code execution, image recognition, audio parsing to web browsing.


## Available Tools

KGoT provides several built-in tools:
- `ExtractZipTool`: Handles extraction of compressed files (`.zip`).
- `SearchTool`: The Surfer Agent which performs web searches.
- `LangchainLLMTool`: Leverages an additional language model to provide extended knowledge beyond the constrained capabilities of the controller's LLM.
- `TextInspectorTool`: Examines textual content in a given file, ranging from transcribed audio from `.mp3` or `.wav` files, spreadsheet data (`.xlsx`, `.csv`) to Powerpoint slides (`.pptx`) or other text-based files such as downloaded web pages (`.html`) or PDF files (`.pdf`).
- `ImageQuestionTool`: Analyzes images and provides captions for the given image.
- `RunPythonCodeTool`: Executes Python code in a sandboxed Docker environment, in which external files from the GAIA tasks are mounted directly into the file system.

> [!NOTE]
> To focus on harnessing the knowledge graph, we reuse several utilities from [AutoGen](https://github.com/microsoft/autogen/tree/gaia_multiagent_v01_march_1st) such as the Browser and MDConverter tools as well as tools from [HuggingFace Agents](https://github.com/aymeric-roucher/GAIA) such as the Surfer Agent, web browsing tools, and the Text Inspector.


## Bookkeeping of Tools

Tools in KGoT are managed through an object of the `ToolManager` class, which maintains the list of available tools.
The `ToolManager` itself can be initialized as follows:
```python3
tool_manager = ToolManager(
    usage_statistics,
    base_config_path="kgot/config_tools.json"
)
```

Note that the `base_config_path` parameter defaults to ["kgot/config_tools.json"](../config_tools.json), which is subsequently parsed for API keys set by the user.
Currently only the `SimpleTextBrowser` utility of the **Surfer Agent** requires the [SerpApi](https://serpapi.com/) API key.

In our reference implementation, the tool manager is initialized within the **KGoT Controller** as an integrated part of the **LLM Tool Executor** component.


## Tool Integration

**To add a new tool:**
1. Initialize the tool
2. Pass in the logger object for tool use statistics
3. Append the tool to the list of the `ToolManager` object

**To remove a tool:**
If you wish to not include a tool, you can simply remove this tool from the list of `self.tools` inside the `ToolManager` object.

All tools must adhere to the [LangChain BaseTool interface class](https://python.langchain.com/api_reference/core/tools/langchain_core.tools.base.BaseTool.html), allowing the tool list to be directly bound to the LLM Tool Executor via LangChain's `bind_tools`.
