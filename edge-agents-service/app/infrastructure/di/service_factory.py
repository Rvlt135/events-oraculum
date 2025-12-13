from app.agents.main_analysis_agent import MainAnalysisAgent
from app.agents.market_agent import MarketAgent
from app.agents.math_agent import MathAgent
from app.agents.meta_gent import MetaAgent
from app.agents.risk_agent import RiskAgent
from app.agents.trend_agent import TrendAgent
from app.infrastructure.cache.catalog.halper import CatalogHalperCache
from app.infrastructure.cache.events.event_analysis import EventAnalysisCache
from app.infrastructure.di.container import Container
from app.pipelines.agents_pipeline import AgentsPipeline
from app.services.event_analysis import EventAnalysisService
from app.services.event_bundle_consumer import EventBundleConsumer

def create_event_bundle_consumer(container: Container) -> EventBundleConsumer:
    catalog_rdb_halper = CatalogHalperCache(container.redis_cache_client)

    return EventBundleConsumer(session_factory=container.session_factory,
                               collector_api_client=container.collector_api_client,
                               catalog_rdb_halper=catalog_rdb_halper)


def create_agents_pipeline(container: Container) -> AgentsPipeline:
    llm_router = container.llm_router
    math_agent = MathAgent(llm=llm_router, prompt_processor=container.prompt_processor)
    market_agent = MarketAgent(llm=llm_router, prompt_processor=container.prompt_processor)
    trend_agent = TrendAgent(llm=llm_router, prompt_processor=container.prompt_processor)
    risk_agent = RiskAgent(llm=llm_router, prompt_processor=container.prompt_processor)
    meta_agent = MetaAgent(llm=llm_router, prompt_processor=container.prompt_processor)
    main_agent = MainAnalysisAgent(llm_router=llm_router, prompt_processor=container.prompt_processor)
    agents_pipeline = AgentsPipeline([math_agent, market_agent, trend_agent, risk_agent, meta_agent], main_agent)
    return agents_pipeline

def create_event_analysis_service(container: Container) -> EventAnalysisService:
    cache = EventAnalysisCache(container.redis_cache_client)
    return EventAnalysisService(container.session_factory, cache)