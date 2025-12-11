# from typing import Dict, TYPE_CHECKING
#
# import structlog
# from prometheus_client import Counter, Histogram
#
# from app.infrastructure.di.container import Container
# from app.infrastructure.di.service_factory import create_event_bundle_consumer
# from app.tasks.broker import broker
#
# if TYPE_CHECKING:
#     pass
#
# logger = structlog.get_logger()
#
# collection_duration = Histogram("event_layer_collection_duration_seconds", "Time spent building event layer")
# events_processed_total = Counter("event_layer_events_processed_total", "Total number of event layer events processed")
# collection_errors_total = Counter("event_layer_collection_errors_total", "Total number of collection errors")
#
#
# @broker.task()
# async def start_event_analysis_task() -> Dict[str, str]:
#     """Collect event feature bundles from fixtures and persist enriched bundles."""
#     logger.debug("collect_event_feature_bundles_task_started")
#
#     if not hasattr(broker.state, 'container'):
#         raise RuntimeError("Container not found in broker.state")
#
#     container: "Container" = broker.state.container
#
#     try:
#         # Resolve services via DI
#         service_team_features = create_event_bundle_consumer(container)
