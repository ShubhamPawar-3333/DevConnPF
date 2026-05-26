"""
Search module for full-text search across AI-generated summaries.

Uses PostgreSQL full-text search (tsvector, tsquery, ts_rank, ts_headline)
as the primary implementation, with a SQLite fallback using LIKE queries
for testing environments.
"""

from dataclasses import dataclass

from django.db import connection

from explorer.models import BlockSummary, FileSummary


@dataclass
class SearchResult:
    """A single search result from the summary search service."""

    file_path: str
    block_name: str | None
    summary_excerpt: str  # Up to 200 chars with match highlighted
    similarity_rank: float
    result_type: str  # "file" or "block"


class QueryValidationError(Exception):
    """Raised when a search query fails validation."""

    pass


def validate_query(query: str) -> str:
    """Validate and clean a search query.

    Args:
        query: The raw search query string.

    Returns:
        The cleaned query string.

    Raises:
        QueryValidationError: If the query is invalid.
    """
    if not query or not query.strip():
        raise QueryValidationError(
            "Search query must be at least 3 characters long."
        )

    cleaned = query.strip()

    if len(cleaned) < 3:
        raise QueryValidationError(
            "Search query must be at least 3 characters long."
        )

    if len(cleaned) > 300:
        raise QueryValidationError(
            "Search query must not exceed 300 characters."
        )

    return cleaned


class SummarySearchService:
    """Service for searching across file and block summaries within a repository."""

    def search(
        self, repository_id: int, query: str, limit: int = 50
    ) -> list[SearchResult]:
        """Search summaries within a repository.

        Uses PostgreSQL full-text search when available, falls back to
        LIKE-based search for SQLite (test environments).

        Args:
            repository_id: The ID of the repository to search within.
            query: The search query string (must be 3-300 characters).
            limit: Maximum number of results to return (default 50).

        Returns:
            List of SearchResult objects ordered by decreasing similarity rank.

        Raises:
            QueryValidationError: If the query fails validation.
        """
        cleaned_query = validate_query(query)

        # Cap limit to 50
        limit = min(limit, 50)

        backend = connection.vendor
        if backend == "postgresql":
            return self._search_postgresql(repository_id, cleaned_query, limit)
        else:
            return self._search_sqlite(repository_id, cleaned_query, limit)

    def _search_postgresql(
        self, repository_id: int, query: str, limit: int
    ) -> list[SearchResult]:
        """Perform full-text search using PostgreSQL tsvector/tsquery."""
        results = []

        # Search FileSummary
        file_results = self._search_file_summaries_pg(repository_id, query, limit)
        results.extend(file_results)

        # Search BlockSummary
        block_results = self._search_block_summaries_pg(repository_id, query, limit)
        results.extend(block_results)

        # Sort by rank descending and limit
        results.sort(key=lambda r: r.similarity_rank, reverse=True)
        return results[:limit]

    def _search_file_summaries_pg(
        self, repository_id: int, query: str, limit: int
    ) -> list[SearchResult]:
        """Search file summaries using PostgreSQL full-text search."""
        sql = """
            SELECT
                rf.path AS file_path,
                ts_rank(fs.summary_vector, plainto_tsquery('english', %s)) AS rank,
                ts_headline(
                    'english',
                    fs.summary_text,
                    plainto_tsquery('english', %s),
                    'MaxWords=35, MinWords=15, MaxFragments=1, StartSel=<mark>, StopSel=</mark>'
                ) AS excerpt
            FROM explorer_filesummary fs
            JOIN explorer_repositoryfile rf ON fs.file_id = rf.id
            WHERE rf.repository_id = %s
              AND fs.summary_vector @@ plainto_tsquery('english', %s)
              AND fs.status = 'completed'
            ORDER BY rank DESC
            LIMIT %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [query, query, repository_id, query, limit])
            rows = cursor.fetchall()

        results = []
        for row in rows:
            file_path, rank, excerpt = row
            # Truncate excerpt to 200 chars
            if len(excerpt) > 200:
                excerpt = excerpt[:197] + "..."
            results.append(
                SearchResult(
                    file_path=file_path,
                    block_name=None,
                    summary_excerpt=excerpt,
                    similarity_rank=float(rank),
                    result_type="file",
                )
            )
        return results

    def _search_block_summaries_pg(
        self, repository_id: int, query: str, limit: int
    ) -> list[SearchResult]:
        """Search block summaries using PostgreSQL full-text search."""
        sql = """
            SELECT
                rf.path AS file_path,
                cb.name AS block_name,
                ts_rank(bs.summary_vector, plainto_tsquery('english', %s)) AS rank,
                ts_headline(
                    'english',
                    bs.summary_text,
                    plainto_tsquery('english', %s),
                    'MaxWords=35, MinWords=15, MaxFragments=1, StartSel=<mark>, StopSel=</mark>'
                ) AS excerpt
            FROM explorer_blocksummary bs
            JOIN explorer_codeblock cb ON bs.block_id = cb.id
            JOIN explorer_repositoryfile rf ON cb.file_id = rf.id
            WHERE rf.repository_id = %s
              AND bs.summary_vector @@ plainto_tsquery('english', %s)
              AND bs.status = 'completed'
            ORDER BY rank DESC
            LIMIT %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [query, query, repository_id, query, limit])
            rows = cursor.fetchall()

        results = []
        for row in rows:
            file_path, block_name, rank, excerpt = row
            # Truncate excerpt to 200 chars
            if len(excerpt) > 200:
                excerpt = excerpt[:197] + "..."
            results.append(
                SearchResult(
                    file_path=file_path,
                    block_name=block_name,
                    summary_excerpt=excerpt,
                    similarity_rank=float(rank),
                    result_type="block",
                )
            )
        return results

    def _search_sqlite(
        self, repository_id: int, query: str, limit: int
    ) -> list[SearchResult]:
        """Fallback search using LIKE queries for SQLite (test environments)."""
        results = []

        # Search FileSummary using Django ORM with LIKE
        file_results = self._search_file_summaries_sqlite(
            repository_id, query, limit
        )
        results.extend(file_results)

        # Search BlockSummary using Django ORM with LIKE
        block_results = self._search_block_summaries_sqlite(
            repository_id, query, limit
        )
        results.extend(block_results)

        # Sort by rank descending and limit
        results.sort(key=lambda r: r.similarity_rank, reverse=True)
        return results[:limit]

    def _search_file_summaries_sqlite(
        self, repository_id: int, query: str, limit: int
    ) -> list[SearchResult]:
        """Search file summaries using LIKE for SQLite."""
        # Split query into words for matching
        query_words = query.lower().split()

        file_summaries = (
            FileSummary.objects.filter(
                file__repository_id=repository_id,
                status="completed",
            )
            .select_related("file")
        )

        results = []
        for fs in file_summaries:
            summary_lower = fs.summary_text.lower()
            # Calculate a simple relevance score based on word matches
            match_count = sum(
                1 for word in query_words if word in summary_lower
            )
            if match_count == 0:
                continue

            # Calculate rank as proportion of query words matched
            rank = match_count / len(query_words)

            # Generate excerpt with highlighting
            excerpt = self._generate_excerpt(fs.summary_text, query_words)

            results.append(
                SearchResult(
                    file_path=fs.file.path,
                    block_name=None,
                    summary_excerpt=excerpt,
                    similarity_rank=rank,
                    result_type="file",
                )
            )

        # Sort by rank and limit
        results.sort(key=lambda r: r.similarity_rank, reverse=True)
        return results[:limit]

    def _search_block_summaries_sqlite(
        self, repository_id: int, query: str, limit: int
    ) -> list[SearchResult]:
        """Search block summaries using LIKE for SQLite."""
        query_words = query.lower().split()

        block_summaries = (
            BlockSummary.objects.filter(
                block__file__repository_id=repository_id,
                status="completed",
            )
            .select_related("block", "block__file")
        )

        results = []
        for bs in block_summaries:
            summary_lower = bs.summary_text.lower()
            match_count = sum(
                1 for word in query_words if word in summary_lower
            )
            if match_count == 0:
                continue

            rank = match_count / len(query_words)
            excerpt = self._generate_excerpt(bs.summary_text, query_words)

            results.append(
                SearchResult(
                    file_path=bs.block.file.path,
                    block_name=bs.block.name,
                    summary_excerpt=excerpt,
                    similarity_rank=rank,
                    result_type="block",
                )
            )

        results.sort(key=lambda r: r.similarity_rank, reverse=True)
        return results[:limit]

    def _generate_excerpt(self, text: str, query_words: list[str]) -> str:
        """Generate a highlighted excerpt from the summary text.

        Finds the first occurrence of any query word and extracts surrounding
        context, marking the match with <mark> tags.

        Args:
            text: The full summary text.
            query_words: List of query words to highlight.

        Returns:
            A string of up to 200 characters with matches highlighted.
        """
        text_lower = text.lower()

        # Find the first matching word position
        best_pos = len(text)
        best_word = ""
        for word in query_words:
            pos = text_lower.find(word)
            if pos != -1 and pos < best_pos:
                best_pos = pos
                best_word = word

        if not best_word:
            # No match found, return truncated text
            return text[:200] if len(text) > 200 else text

        # Calculate excerpt window around the match
        excerpt_len = 200
        match_len = len(best_word)

        # Center the excerpt around the match
        start = max(0, best_pos - 50)
        end = min(len(text), start + excerpt_len - 13)  # Account for <mark></mark> tags

        excerpt = text[start:end]

        # Highlight the matched word in the excerpt
        excerpt_lower = excerpt.lower()
        for word in query_words:
            word_pos = excerpt_lower.find(word)
            if word_pos != -1:
                original_word = excerpt[word_pos : word_pos + len(word)]
                excerpt = (
                    excerpt[:word_pos]
                    + f"<mark>{original_word}</mark>"
                    + excerpt[word_pos + len(word) :]
                )
                break  # Only highlight first occurrence to keep within length

        # Truncate to 200 chars if needed
        if len(excerpt) > 200:
            excerpt = excerpt[:197] + "..."

        return excerpt
