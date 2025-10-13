from prometheus_client import Counter, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

def init_metrics(app):
    registry = CollectorRegistry()
    http_requests_total = Counter(
        "odds_service_http_requests_total",
        "Total HTTP requests",
        ["method", "path", "route_type"],
        registry=registry,                 # <- ключевое
    )
    app.state.metrics_registry = registry
    app.state.http_requests_total = http_requests_total

def metrics_endpoint(app):
    async def endpoint():
        data = generate_latest(app.state.metrics_registry)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)
    return endpoint