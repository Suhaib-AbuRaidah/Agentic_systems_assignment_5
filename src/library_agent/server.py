"""FastMCP server exposing exactly one data, action, and orchestration tool."""

from fastmcp import FastMCP

from .service import FindAndSaveResult, LibraryService, SaveResult, SearchResult


mcp = FastMCP("campus-library")
library = LibraryService()


@mcp.tool()
def search_catalog(query: str) -> SearchResult:
    """DATA: Search the demo catalog of real published books by title, author, subject, or ID. Never modifies the reading list. Rejects blank queries."""
    return library.search_catalog(query)


@mcp.tool()
def save_to_reading_list(book_id: str) -> SaveResult:
    """ACTION: Save one known book ID to a persistent local reading list. Rejects unknown IDs; duplicate saves are reported without adding a second row."""
    return library.save_to_reading_list(book_id)


@mcp.tool()
def find_and_save_book(query: str) -> FindAndSaveResult:
    """ORCHESTRATION: Search the catalog, require exactly one match, then save it to the reading list. Rejects missing or ambiguous matches before writing."""
    return library.find_and_save_book(query)


def main() -> None:
    mcp.run(transport="stdio", stateless=True, show_banner=False)


if __name__ == "__main__":
    main()
