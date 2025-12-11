from app.agents.main_analysis_agent import MainAnalysisAgent
from app.agents.market_agent import MarketAgent
from app.agents.math_agent import MathAgent
from app.infrastructure.cache.catalog.halper import CatalogHalperCache
from app.infrastructure.di.container import Container
from app.pipelines.agents_pipeline import AgentsPipeline
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
    main_agent = MainAnalysisAgent(llm_router=llm_router, prompt_processor=container.prompt_processor)
    agents_pipeline = AgentsPipeline([math_agent, market_agent], main_agent)
    return agents_pipeline