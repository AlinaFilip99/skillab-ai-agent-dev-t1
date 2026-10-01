import inspect
from pydantic import BaseModel

TOOL_REGISTRY: dict[str, callable] = {}

def register_tool(func):
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    # Validare 1: un singur param de tip BaseModel
    if len(params) != 1 or not issubclass(
        params[0].annotation, BaseModel
    ):
        raise TypeError(
            f"{func.__name__}: unique param of type BaseModel required"
        )

    # Validare 2: docstring obligatoriu (devine description pentru LLM)
    docstring = (func.__doc__ or "").strip()
    if not docstring:
        raise ValueError(
            f"{func.__name__}: docstring mandatory — becomes "
            f"description visible for LLM."
        )
    if len(docstring) < 15:
        raise ValueError(
            f"{func.__name__}: docstring too short ({len(docstring)} "
            f"characters). LLM needs at least 15 characters to make a decision."
        )
    
    TOOL_REGISTRY[func.__name__] = {
        "func": func,
        "params_model": params[0].annotation,
        "description": docstring,  # ← asta primește LLM-ul
    }
    return func

