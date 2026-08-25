# Declarative topology — compiled in app/workflows/compiler/compiler.py
WORKFLOW_CONFIGS = {
    "orchestrator": {
        "entry": "check_confirmation",
        "exit": "end",
        "nodes": ["check_confirmation", "model", "tools", "request_confirmation", "execute_action"],
        "edges": [("tools", "model")],
        "routers": {"check_confirmation": "after_check_confirmation", "model": "route_after_model"},
    }
}
