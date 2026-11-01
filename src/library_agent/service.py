"""Business logic shared by the three MCP tools."""

import os
import sqlite3
from pathlib import Path

from pydantic import BaseModel

from .catalog import Book, CATALOG


class SearchResult(BaseModel):
    query: str
    matches: list[Book]
    count: int


class SaveResult(BaseModel):
    book: Book
    saved: bool
    already_saved: bool


class FindAndSaveResult(BaseModel):
    query: str
    book: Book
    saved: bool
    already_saved: bool


class LibraryService:
    def __init__(self, db_path: Path | None = None):
        configured_path = os.getenv("LIBRARY_DB_PATH")
        self.db_path = db_path or (
            Path(configured_path) if configured_path else Path(__file__).resolve().parents[2] / "data" / "reading_list_real_books.sqlite3"
        )

    def search_catalog(self, query: str) -> SearchResult:
        """Return matching books without changing state."""
        normalized = query.strip().casefold()
        if not normalized:
            raise ValueError("Query must contain at least one non-space character.")
        matches = [
            book for book in CATALOG
            if normalized in " ".join((book.id, book.title, book.author, book.subject)).casefold()
        ]
        return SearchResult(query=query.strip(), matches=matches, count=len(matches))

    def save_to_reading_list(self, book_id: str) -> SaveResult:
        """Persist one catalog book once in the local reading list."""
        normalized = book_id.strip().upper()
        if not normalized:
            raise ValueError("Book ID must not be empty.")
        book = next((item for item in CATALOG if item.id == normalized), None)
        if book is None:
            raise ValueError(f"Unknown book ID: {normalized}.")

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS reading_list (book_id TEXT PRIMARY KEY, saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            cursor = connection.execute(
                "INSERT OR IGNORE INTO reading_list (book_id) VALUES (?)", (book.id,)
            )
        inserted = cursor.rowcount == 1
        return SaveResult(book=book, saved=inserted, already_saved=not inserted)

    def find_and_save_book(self, query: str) -> FindAndSaveResult:
        """Search, require exactly one match, then save that book."""
        result = self.search_catalog(query)
        if result.count == 0:
            raise ValueError(f"No catalog book matches {result.query!r}.")
        if result.count > 1:
            ids = ", ".join(book.id for book in result.matches)
            raise ValueError(f"Search is ambiguous ({ids}); use an exact title or book ID.")
        save = self.save_to_reading_list(result.matches[0].id)
        return FindAndSaveResult(
            query=result.query,
            book=save.book,
            saved=save.saved,
            already_saved=save.already_saved,
        )
