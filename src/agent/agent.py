from pydantic_ai import Agent, RunContext
from datetime import datetime
from src.search.exa import exa_search
from src.search.crawler import extract_web_content
from src.utils.logger import get_logger
import logfire


logfire.configure()
logfire.instrument_pydantic_ai()

logger = get_logger()


research_agent = Agent("gemini-2.5-flash-preview-05-20")


@research_agent.system_prompt
def system_prompt() -> str:
    return f"""You are an expert research assistant. Your task is to help users find and synthesize information from the web.

    CRITICAL REQUIREMENTS:
    1. Break down complex questions into 4 sub-questions.
    2. Use the Search tool to find information from the web by passing the original question and your 4 sub-questions as a list.
    3. ALWAYS include the full URL in your citations. Every fact, quote, or piece of information MUST be cited with its source URL.
    4. Format citations as: "According to [Source Title](URL), ..." or "As reported by [Source Title](URL)..."
    5. Never provide information without a proper URL citation.
    6. If you cannot find a URL for a piece of information, clearly state that the source is unavailable.

    CITATION FORMAT EXAMPLES:
    - "According to [Tesla's Report](https://tesla.com/), the Model S has a 5-star safety rating."
    - "As reported by [Consumer Reports](https://consumerreports.org/cars/), electric vehicles show 40% fewer maintenance issues."

    Focus on accuracy, clarity, and MANDATORY URL citation of all sources. Today's date is {datetime.now().strftime("%Y-%m-%d")}."""

@research_agent.tool
async def search(ctx: RunContext[str], query: str | list[str], num_results: int = 5) -> dict:
    """Search the web for the given query and return content from results.

    Args:
        ctx: The run context containing dependencies
        query: The search query string
        num_results: Number of search results to retrieve

    Returns:
        Dictionary containing extracted content from web pages
    """

    query_list = [query] if isinstance(query, str) else query

    logger.info(f"Searching for: {query_list}")

    results = await exa_search(query=query_list, num_results=num_results)
    urls = [result.url for result in results]

    logger.info(f"Extracting content from {len(urls)} URLs for query: {query_list}")

    contents = await extract_web_content(urls=urls, content_filter="safety features")

    return contents
