import asyncio
import re
from typing import Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

from src.utils.logger import get_logger
from src.models import ExtractionResult

from groq import Groq

logger = get_logger()

client = Groq()


def llama_guard(text: str) -> float:
    completion = client.chat.completions.create(
        model="meta-llama/llama-prompt-guard-2-86m",
        messages=[{"role": "user", "content": text}],
        temperature=1,
        max_completion_tokens=100,
        top_p=1,
        stream=False,
        stop=None,
    )

    return float(completion.choices[0].message.content)


class ContentExtractor:
    """Simple content extractor for web pages."""

    def __init__(
        self, headless: bool = True, timeout: int = 30, user_agent: Optional[str] = None
    ):
        """Initialize the content extractor.

        Args:
            headless: Whether to run browser in headless mode
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
        """
        self.browser_config = BrowserConfig(
            headless=headless,
            verbose=False,
            user_agent=user_agent or "AI-Research-Assistant/1.0",
        )
        self.timeout = timeout

    def _clean_content(self, content: str) -> str:
        """Clean extracted content by removing excessive whitespace and artifacts.

        Args:
            content: Raw content to clean

        Returns:
            Cleaned content string
        """
        if not content:
            return ""

        # Remove excessive whitespace
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)
        content = re.sub(r"\s+", " ", content)

        # Remove common navigation and UI elements
        lines = content.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip common UI/navigation patterns
            skip_patterns = [
                r"^(Menu|Navigation|Skip to|Cookie|Privacy|Terms|Subscribe|Sign up|Log in).*",
                r"^\d+$",  # Just numbers
                r"^[|•·→←↑↓\-\s]+$",  # Just symbols/separators
                r"^(Share|Tweet|Facebook|LinkedIn|Print)$",
                r"^Copyright.*\d{4}.*",
            ]

            if any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns):
                continue

            # Keep lines with substantial content (more than 10 characters)
            if len(line) > 10:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    def _extract_title(self, html: str) -> Optional[str]:
        """Extract page title from HTML.

        Args:
            html: HTML content

        Returns:
            Page title if found, None otherwise
        """
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        return None

    async def extract_content(
        self, url: str, content_filter: Optional[str] = None
    ) -> ExtractionResult:
        """Extract content from a single URL.

        Args:
            url: URL to extract content from
            content_filter: Optional filter query for content pruning

        Returns:
            ExtractionResult containing the extracted content
        """
        try:
            logger.info(f"Extracting content from: {url}")

            # Configure crawler
            filter_strategy = (
                PruningContentFilter(user_query=content_filter)
                if content_filter
                else PruningContentFilter()
            )

            config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                markdown_generator=DefaultMarkdownGenerator(content_filter=filter_strategy),
            )

            # Extract content
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(url=url, config=config)

            if not result.success:
                return ExtractionResult(
                    url=url, success=False, error="Failed to fetch content from URL"
                )

            # Extract and clean content
            raw_content = getattr(result, "markdown_v2", None)
            if raw_content and hasattr(raw_content, "raw_markdown"):
                content = raw_content.raw_markdown
            else:
                content = getattr(result, "markdown", "")

            cleaned_content = self._clean_content(content)
            title = self._extract_title(getattr(result, "html", ""))

            logger.info(
                f"Successfully extracted {len(cleaned_content)} characters from {url}"
            )

            guard_result = llama_guard(cleaned_content)

            if guard_result > 0.6:
                return ExtractionResult(
                    url=url, success=True, content=cleaned_content, title=title
                )
            else:
                return ExtractionResult(
                    url=url, success=False, error="Content blocked by Llama Guard"
                )

        except Exception as e:
            logger.error(f"Content extraction failed for {url}: {str(e)}")
            return ExtractionResult(url=url, success=False, error=str(e))

    async def extract_multiple(
        self, urls: list[str], max_concurrent: int = 10, content_filter: Optional[str] = None
    ) -> dict[str, ExtractionResult]:
        """Extract content from multiple URLs concurrently.

        Args:
            urls: List of URLs to extract content from
            max_concurrent: Maximum number of concurrent extractions
            content_filter: Optional filter query for content pruning

        Returns:
            Dictionary mapping URLs to their extraction results
        """
        if not urls:
            return {}

        logger.info(f"Extracting content from {len(urls)} URLs")

        # semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_extract(url: str) -> tuple[str, ExtractionResult]:
            # async with semaphore:
            result = await self.extract_content(url, content_filter)
            return url, result

        # Execute extractions concurrently
        results = await asyncio.gather(
            *[bounded_extract(url) for url in urls], return_exceptions=True
        )

        # Process results
        extraction_results = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Extraction failed with exception: {str(result)}")
                continue

            url, extraction_result = result
            extraction_results[url] = extraction_result

        successful_extractions = sum(1 for r in extraction_results.values() if r.success)
        logger.info(
            f"Content extraction completed: {successful_extractions}/{len(urls)} successful"
        )

        logger.debug(f"extract_multiple returned: {extraction_results}")

        return extraction_results


# Convenience function
async def extract_web_content(
    urls: str | list[str], content_filter: Optional[str] = None
) -> dict[str, ExtractionResult] | ExtractionResult:
    """Convenience function to extract content from web URLs.

    Args:
        urls: Single URL string or list of URLs
        content_filter: Optional filter query for content pruning

    Returns:
        Single ExtractionResult for single URL, or dict of results for multiple URLs
    """
    extractor = ContentExtractor()

    if isinstance(urls, str):
        return await extractor.extract_content(urls, content_filter)
    else:
        return await extractor.extract_multiple(urls, content_filter=content_filter)
