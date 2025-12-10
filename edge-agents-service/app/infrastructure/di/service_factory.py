from app.agents.main_analysis_agent import MainAnalysisAgent
from app.agents.market_agent import MarketAgent
from app.agents.math_agent import MathAgent
from app.infrastructure.cache import RecommendationCache
from app.infrastructure.cache.catalog.halper import CatalogHalperCache
from app.infrastructure.di.container import Container
from app.llm.llm_router import LLMRouter
from app.pipelines.agents_pipeline import AgentsPipeline
from app.services.event_bundle_consumer import EventBundleConsumer
from app.services.legacy.features import FeatureService
from app.services.legacy.service import RecommendationService


def create_recommendation_service(container: Container) -> RecommendationService:
    recommendation_cache = RecommendationCache(container.redis_cache_client)

    return RecommendationService(session_factory=container.session_factory, cache=recommendation_cache)

def create_feature_service(container: Container) -> FeatureService:
    return FeatureService(session_factory=container.session_factory)

def create_event_bundle_consumer(container: Container) -> EventBundleConsumer:
    catalog_rdb_halper = CatalogHalperCache(container.redis_cache_client)

    return EventBundleConsumer(session_factory=container.session_factory,
                               collector_api_client=container.collector_api_client,
                               catalog_rdb_halper=catalog_rdb_halper)


def create_agents_pipeline(container: Container) -> AgentsPipeline:
    llm_router = container.llm_router
    math_agent = MathAgent(llm=llm_router)
    market_agent = MarketAgent(llm=llm_router)
    main_agent = MainAnalysisAgent(llm_router=llm_router)
    agents_pipeline = AgentsPipeline([math_agent, market_agent], main_agent)
    return agents_pipeline