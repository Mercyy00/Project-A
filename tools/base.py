from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    """Standardized response returned by all Jarvis tools."""
    success: bool = Field(description="True if tool executed successfully, False otherwise")
    data: Any = Field(default=None, description="Structured payload or output data")
    message: str = Field(description="Human and LLM readable summary of execution result")

    def to_llm_string(self) -> str:
        """Format the result as a clear string for the LLM context."""
        status = "SUCCESS" if self.success else "FAILED"
        data_str = f"\nData: {self.data}" if self.data is not None else ""
        return f"[{status}] {self.message}{data_str}"

class BaseTool:
    """Base class for all Jarvis system & automation tools."""
    name: str = ""
    description: str = ""

    def run(self, **kwargs) -> ToolResult:
        """Execute the tool logic and return a ToolResult."""
        raise NotImplementedError("Subclasses must implement run()")

    def get_schema(self) -> Dict[str, Any]:
        """Returns JSON schema definition for LLM tool/function calling."""
        # Can be overridden or generated dynamically
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
