"""Optional Arize Phoenix observability.

Fully no-op unless PHOENIX_ENABLED=1. When enabled, it auto-instruments the
Anthropic client so every Claude call the app makes (retention message
generation in offer_engine) is traced: prompt, response, latency, token usage,
and any errors. No changes are required in offer_engine.py because the
instrumentation patches the Anthropic SDK at the library level.

Env vars:
  PHOENIX_ENABLED              "1" to turn tracing on (default off)
  PHOENIX_COLLECTOR_ENDPOINT   Phoenix endpoint (default http://localhost:6006)
  PHOENIX_PROJECT              project name shown in the UI (default churnshield)

To use locally:
  pip install -r requirements-observability.txt
  phoenix serve                 # starts the UI at http://localhost:6006
  PHOENIX_ENABLED=1 uvicorn app.main:app --reload
"""
import os

_initialized = False


def _enabled() -> bool:
    return os.getenv("PHOENIX_ENABLED", "").strip().lower() in ("1", "true", "yes")


def init_observability() -> bool:
    """Initialize Phoenix tracing. Returns True if tracing is active.

    Never raises: if Phoenix or the instrumentor is not installed, or the
    collector is unreachable, the app continues normally without tracing.
    """
    global _initialized
    if _initialized:
        return True
    if not _enabled():
        return False
    try:
        from phoenix.otel import register
        from openinference.instrumentation.anthropic import AnthropicInstrumentor

        endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006").rstrip("/")
        register(
            project_name=os.getenv("PHOENIX_PROJECT", "churnshield"),
            endpoint=f"{endpoint}/v1/traces",
            set_global_tracer_provider=True,
        )
        AnthropicInstrumentor().instrument()
        _initialized = True
        print(f"[observability] Phoenix tracing enabled -> {endpoint} (project=churnshield)")
        return True
    except Exception as e:  # pragma: no cover - defensive, never break the app
        print(f"[observability] Phoenix not enabled ({type(e).__name__}: {e}); continuing without tracing.")
        return False
