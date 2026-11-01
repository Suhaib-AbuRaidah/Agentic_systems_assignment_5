import sqlite3

import pytest

from library_agent.service import LibraryService


@pytest.fixture
def library(tmp_path):
    return LibraryService(tmp_path / "reading-list.sqlite3")


def test_search_is_read_only(library):
    result = library.search_catalog("Python")
    assert result.count == 2
    assert {book.id for book in result.matches} == {"LIB-102", "LIB-106"}
    assert not library.db_path.exists()


def test_search_rejects_blank_query(library):
    with pytest.raises(ValueError, match="non-space"):
        library.search_catalog("   ")


def test_save_persists_once(library):
    first = library.save_to_reading_list("lib-103")
    second = library.save_to_reading_list("LIB-103")
    assert first.saved and not first.already_saved
    assert not second.saved and second.already_saved
    with sqlite3.connect(library.db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM reading_list").fetchone()[0] == 1


def test_save_rejects_unknown_id_without_writing(library):
    with pytest.raises(ValueError, match="Unknown book ID"):
        library.save_to_reading_list("LIB-999")
    assert not library.db_path.exists()


def test_orchestration_searches_then_saves(library):
    result = library.find_and_save_book("Designing Data-Intensive Applications")
    assert result.book.id == "LIB-103"
    assert result.saved
    assert library.save_to_reading_list("LIB-103").already_saved


def test_orchestration_rejects_missing_and_ambiguous_matches(library):
    with pytest.raises(ValueError, match="No catalog book"):
        library.find_and_save_book("marine biology")
    with pytest.raises(ValueError, match="ambiguous"):
        library.find_and_save_book("Python")
    assert not library.db_path.exists()
