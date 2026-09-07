"""LangGraph StateGraph builder for Augury supervisor."""

from functools import partial
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from augury.graph.state import AuguryGraphState
from augury.graph.nodes import (
    node_load_context,
    node_strategist,
    node_validate_plan,
    node_strategist_repair,
    node_approval_gate,
    node_founder_revision,
    node_execute,
    node_measure,
    node_analyst,
    node_validate_analysis,
    node_persist_ledger,
    node_generate_digest,
)
from augury.graph.routing import (
    route_after_validation,
    route_after_approval,
    route_after_digest,
)


def compile_augury_graph(
    ledger,
    profiler,
    intake,
    strategist_agent,
    analyst_agent,
    approval_gate,
    execution_service,
    measurement_service,
    digest_service,
    checkpointer=None,
    on_node_start=None,
    content_agent=None,
):
    """Construct and compile the LangGraph StateGraph workflow for Augury."""
    workflow = StateGraph(AuguryGraphState)

    # Register nodes with dependency injection
    workflow.add_node("load_context", partial(node_load_context, ledger=ledger, profiler=profiler, intake=intake))
    workflow.add_node("strategist", partial(node_strategist, strategist_agent=strategist_agent, ledger=ledger))
    workflow.add_node("validate_plan", node_validate_plan)
    workflow.add_node("strategist_repair", partial(node_strategist_repair, strategist_agent=strategist_agent))
    workflow.add_node("approval_gate", partial(node_approval_gate, approval_gate=approval_gate))
    workflow.add_node("founder_revision", node_founder_revision)
    workflow.add_node("execute", partial(node_execute, execution_service=execution_service))
    workflow.add_node("measure", partial(node_measure, measurement_service=measurement_service))
    workflow.add_node("analyst", partial(node_analyst, analyst_agent=analyst_agent))
    workflow.add_node("validate_analysis", node_validate_analysis)
    workflow.add_node("persist_ledger", partial(node_persist_ledger, ledger=ledger))
    workflow.add_node("generate_digest", partial(node_generate_digest, digest_service=digest_service))

    # Edges
    workflow.add_conditional_edges(START, lambda state: "execute" if state.get("approved_plan") and state.get("approval_status") == "APPROVED" else "load_context")
    workflow.add_edge("load_context", "strategist")
    workflow.add_edge("strategist", "validate_plan")

    if content_agent is not None:
        def generate_content(state):
            package = content_agent.generate_content(state['cycle_id'], state['proposed_plan'],
                founder_brief=state['founder_brief'], startup_profile=state['startup_profile'])
            return {'content_package': package.model_dump(mode='json')}
        workflow.add_node('content', generate_content)
        workflow.add_edge('content', 'approval_gate')

    workflow.add_conditional_edges(
        "validate_plan",
        route_after_validation,
        {
            "approval_gate": "content" if content_agent is not None else "approval_gate",
            "strategist_repair": "strategist_repair",
            END: END
        }
    )

    workflow.add_edge("strategist_repair", "validate_plan")

    workflow.add_conditional_edges(
        "approval_gate",
        route_after_approval,
        {
            "execute": "execute",
            "founder_revision": "founder_revision",
            "end": END,
        }
    )

    workflow.add_edge("founder_revision", "strategist")

    workflow.add_edge("execute", "measure")
    workflow.add_edge("measure", "analyst")
    workflow.add_edge("analyst", "validate_analysis")
    workflow.add_edge("validate_analysis", "persist_ledger")
    workflow.add_edge("persist_ledger", "generate_digest")

    workflow.add_conditional_edges(
        "generate_digest",
        route_after_digest,
        {
            "load_context": "load_context",
            END: END
        }
    )

    if on_node_start is not None:
        # Wrap the registered runnable rather than guessing the next node in the UI.
        from langchain_core.runnables import RunnableLambda
        for name, spec in workflow.nodes.items():
            runnable = spec.runnable
            def report_and_invoke(state, config, name=name, runnable=runnable):
                on_node_start(name)
                return runnable.invoke(state, config)
            spec.runnable = RunnableLambda(report_and_invoke)

    # A checkpointer is useful for resumable/streaming deployments, but a
    # plain graph invocation should also work for local scripts and tests.
    # LangGraph requires a configurable thread_id whenever a checkpointer is
    # attached, and state-level thread_id is not sufficient for that API.
    if checkpointer is None:
        return workflow.compile()
    return workflow.compile(checkpointer=checkpointer)
