"""API and Bedrock AgentCore serving layer.

``entrypoint`` (the graph-backed AgentCore handler) is imported lazily so that
importing a standalone service in this package - e.g.
``augury.api.analyst_lambda`` - does not drag in the LangGraph supervisor or
any orchestration state.
"""

__all__ = ["entrypoint"]


def __getattr__(name: str):
    if name == "entrypoint":
        from augury.api.agentcore_app import entrypoint

        return entrypoint
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
