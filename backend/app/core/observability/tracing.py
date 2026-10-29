import time
from contextlib import contextmanager

@contextmanager
def trace_span(span_name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        # Can be emitted to OpenTelemetry / Datadog
