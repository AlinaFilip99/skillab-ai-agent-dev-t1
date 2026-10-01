from .registry import TOOL_REGISTRY

class ToolWrapper:
    @staticmethod
    def call(name: str, args: dict) -> str:
        # 1. Lookup în registry
        if name not in TOOL_REGISTRY:
            return f"Error: tool '{name}' does not exist."

        tool = TOOL_REGISTRY[name]

        # 2. Validate — Pydantic verifică tipuri și constrângeri
        try:
            params = tool["params_model"](**args)
        except Exception as e:
            return f"Error validating '{name}': {e}"

        # 3. Execute + 4. Return
        try:
            return str(tool["func"](params))
        except Exception as e:
            return f"Error executing '{name}': {e}"

    @staticmethod
    def catalog_google() -> list[dict]:
        # Iterează registry → JSON Schema per tool (format Google)
        return [
            {
                "name": name,
                "description": tool["description"],
                "parameters": tool["params_model"].model_json_schema(),
            }
            for name, tool in TOOL_REGISTRY.items()
        ]
