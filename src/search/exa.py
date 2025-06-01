from src.utils.logger import get_logger
from typing import Optional
from ..models import SearchResult, ExaSearchException
from exa_py import Exa
import asyncio
import os

logger = get_logger()


class ExaSearchTool:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        if not self.api_key:
            raise ExaSearchException(
                "EXA API key must be provided or set in EXA_API_KEY environment variable"
            )

        self.exa = Exa(self.api_key)
        logger.info("EXA Search Tool initialized successfully")

    async def search(
        self,
        query: str,
        search_type: str = "auto",
        category: Optional[str] = None,
        num_results: int = 5,
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[list[str]] = None,
        exclude_text: Optional[list[str]] = None,
        include_contents: bool = True,
        summary_query: Optional[str] = None,
        subpages: int = 0,
        subpage_target: str = "sources",
        include_links: bool = False,
        include_image_links: bool = False,
    ) -> list[SearchResult]:
        """
        Perform web search using EXA API.

        Args:
            query: The search query string (e.g., "Latest developments in AI")
            search_type: Type of search - "auto", "neural", or "keyword". Default is "auto"
            category: Data category to focus on - "company", "research paper", "news", "pdf",
                     "github", "tweet", "personal site", "linkedin profile", "financial report"
            num_results: Number of results to return (1-100). Default is 10
            include_domains: List of domains to include (e.g., ["arxiv.org", "github.com"])
            exclude_domains: List of domains to exclude
            start_crawl_date: Include links crawled after this date (ISO 8601 format)
            end_crawl_date: Include links crawled before this date (ISO 8601 format)
            start_published_date: Include links published after this date (ISO 8601 format)
            end_published_date: Include links published before this date (ISO 8601 format)
            include_text: List of strings that must be present in webpage text (max 1 string, 5 words)
            exclude_text: List of strings that must not be present in webpage text (max 1 string, 5 words)
            include_contents: Whether to include page contents in results. Default is True
            summary_query: Query for AI-generated summary of the content
            subpages: Number of subpages to crawl (0-5). Default is 0
            subpage_target: Target for subpage crawling - "sources" or "links"
            include_links: Whether to include links in results
            include_image_links: Whether to include image links in results
            include_favicon: Whether to include favicon URLs in results

        Returns:
            SearchResponse: Structured search results with metadata
        """
        # Input validation
        if not query or not query.strip():
            raise ExaSearchException("Query cannot be empty")

        if num_results < 1 or num_results > 100:
            raise ExaSearchException("num_results must be between 1 and 100")

        if search_type not in ["auto", "neural", "keyword"]:
            raise ExaSearchException("search_type must be 'auto', 'neural', or 'keyword'")

        if subpages < 0 or subpages > 5:
            raise ExaSearchException("subpages must be between 0 and 5")

        logger.info(f"Performing search for query: '{query}' with {num_results} results")

        try:
            # Prepare search parameters
            search_params = {
                "query": query.strip(),
                "type": search_type,
                "num_results": num_results,
                "text": include_contents,
            }

            # Add optional parameters
            if category:
                search_params["category"] = category
            if include_domains:
                search_params["include_domains"] = include_domains
            if exclude_domains:
                search_params["exclude_domains"] = exclude_domains
            if start_crawl_date:
                search_params["start_crawl_date"] = start_crawl_date
            if end_crawl_date:
                search_params["end_crawl_date"] = end_crawl_date
            if start_published_date:
                search_params["start_published_date"] = start_published_date
            if end_published_date:
                search_params["end_published_date"] = end_published_date
            if include_text:
                search_params["include_text"] = include_text
            if exclude_text:
                search_params["exclude_text"] = exclude_text
            if summary_query:
                search_params["summary"] = {"query": summary_query}
            if subpages > 0:
                search_params["subpages"] = subpages
                search_params["subpage_target"] = subpage_target

            # Handle extras
            extras = {}
            if include_links:
                extras["links"] = 1
            if include_image_links:
                extras["image_links"] = 1
            if extras:
                search_params["extras"] = extras

            # Perform search in thread pool for async compatibility
            loop = asyncio.get_event_loop()
            raw_results = await loop.run_in_executor(
                None, lambda: self.exa.search_and_contents(**search_params)
            )

            # Parse and structure results
            search_results = []
            for result in raw_results.results:
                search_result = SearchResult(
                    title=result.title or "No title",
                    url=result.url,
                    published_date=result.published_date,
                    author=result.author,
                    score=result.score or 0.0,
                    text=getattr(result, "text", None),
                    summary=getattr(result, "summary", None),
                )
                search_results.append(search_result)

            logger.info(
                f"Search completed successfully. Found {len(search_results)} results"
            )
            return search_results

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            raise ExaSearchException(f"EXA search failed: {str(e)}") from e

    def search_sync(self, query: str, **kwargs) -> list[SearchResult]:
        """
        Synchronous version of the search method.

        Args:
            query: The search query string
            **kwargs: All other parameters from the async search method

        Returns:
            list[SearchResult]: Structured search results
        """
        return asyncio.run(self.search(query, **kwargs))

    async def multi_search(
        self, queries: list[str], max_concurrent: int = 10, **kwargs
    ) -> list[list[SearchResult]]:
        """
        Perform multiple searches concurrently.

        Args:
            queries: List of search queries to execute
            max_concurrent: Maximum number of concurrent searches. Default is 3
            **kwargs: Parameters to apply to all searches

        Returns:
            list[list[SearchResult]]: List of search responses in the same order as queries
        """
        if not queries:
            return []

        if isinstance(queries, str):
            queries = [queries]

        logger.info(f"Performing {len(queries)} concurrent searches")

        # semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_search(query: str) -> SearchResult:
            # async with semaphore:
            return await self.search(query, **kwargs)

        results = await asyncio.gather(
            *[bounded_search(query) for query in queries], return_exceptions=True
        )

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, ExaSearchException):
                logger.error(f"Search failed for query '{queries[i]}': {str(result)}")
                processed_results.extend([])  # Return empty list for failed searches
            else:
                processed_results.extend(result)

        logger.info(f"Multi-search completed. {len(processed_results)} responses returned")
        return processed_results


# Convenience function for backward compatibility
async def exa_search(
    query: str | list[str], **kwargs
) -> list[SearchResult] | list[list[SearchResult]]:
    """
    Convenience function to perform a single EXA search.

    Args:
        query: The search query string
        **kwargs: All parameters supported by ExaSearchTool.search()

    Returns:
        list[SearchResult] or list[list[SearchResult]]: Structured search results
    """
    tool = ExaSearchTool()

    if isinstance(query, list) and len(query) > 0:
        return await tool.multi_search(query, **kwargs)
    else:
        single_query = query[0] if isinstance(query, list) else query
        return await tool.search(single_query, **kwargs)
