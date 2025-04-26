import asyncio
import os
import redis
from rq import Worker, Queue, Connection
from orchestrator import LinkedInScraperOrchestrator
from utils.logging_config import LoggingConfig

# Configure logging
logger = LoggingConfig.setup_logging("worker")

class ScraperWorker:
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.max_workers = int(os.getenv('MAX_WORKERS', '10'))
        self.concurrent_tasks = int(os.getenv('CONCURRENT_TASKS', '3'))
        self.orchestrator = None

    async def setup(self):
        self.orchestrator = LinkedInScraperOrchestrator(
            max_browsers=self.concurrent_tasks,
            use_proxies=True
        )
        await self.orchestrator.setup()

    async def process_url(self, url, entity_type='company'):
        try:
            if entity_type == 'company':
                result = await self.orchestrator.scrape_company(url)
            elif entity_type == 'job':
                result = await self.orchestrator.scrape_job(url)
            elif entity_type == 'profile':
                result = await self.orchestrator.scrape_profile(url)
            return result
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            return None

    async def cleanup(self):
        if self.orchestrator:
            await self.orchestrator.cleanup()

async def main():
    worker = ScraperWorker()
    await worker.setup()

    try:
        redis_conn = redis.from_url(worker.redis_url)
        with Connection(redis_conn):
            queue = Queue('linkedin_scraper')
            worker = Worker([queue])
            worker.work()
    finally:
        await worker.cleanup()

if __name__ == "__main__":
    asyncio.run(main())