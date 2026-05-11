"""Behavioral characterisation tests for books.py.

These tests pin the current behavior of every public method in
BookCollection and the module-level get_stats function so that
refactoring can be done safely. They complement the existing
test_books.py without duplicating its get_stats coverage.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import books
from books import (
    Book,
    BookAppError,
    BookCollection,
    BookNotFoundError,
    BookStats,
    BookStorageError,
    BookValidationError,
    get_stats,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_data_file(tmp_path, monkeypatch):
    """Redirect DATA_FILE to a temp path so tests never touch the real file."""
    temp_file = tmp_path / "data.json"
    temp_file.write_text("[]")
    monkeypatch.setattr(books, "DATA_FILE", str(temp_file))


@pytest.fixture
def collection():
    return BookCollection()


@pytest.fixture
def populated_collection():
    col = BookCollection()
    col.add_book("1984", "George Orwell", 1949)
    col.add_book("Dune", "Frank Herbert", 1965)
    col.add_book("Dune Messiah", "Frank Herbert", 1969)
    return col


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:
    """All custom exceptions must be catchable as BookAppError."""

    def test_book_not_found_is_book_app_error(self):
        assert issubclass(BookNotFoundError, BookAppError)

    def test_book_storage_error_is_book_app_error(self):
        assert issubclass(BookStorageError, BookAppError)

    def test_book_validation_error_is_book_app_error(self):
        assert issubclass(BookValidationError, BookAppError)

    def test_catch_validation_error_as_base(self, collection):
        with pytest.raises(BookAppError):
            collection.add_book("", "Author", 2000)

    def test_catch_not_found_error_as_base(self, collection):
        with pytest.raises(BookAppError):
            collection.mark_as_read("No Such Book")


# ---------------------------------------------------------------------------
# load_books
# ---------------------------------------------------------------------------

class TestLoadBooks:
    """BookCollection.load_books — file reading and error recovery."""

    def test_missing_file_gives_empty_collection(self, tmp_path, monkeypatch):
        monkeypatch.setattr(books, "DATA_FILE", str(tmp_path / "nonexistent.json"))
        col = BookCollection()
        assert col.books == []

    def test_valid_json_loads_books(self, tmp_path, monkeypatch):
        data_file = tmp_path / "data.json"
        data_file.write_text(
            json.dumps([{"title": "1984", "author": "George Orwell", "year": 1949, "read": False}])
        )
        monkeypatch.setattr(books, "DATA_FILE", str(data_file))
        col = BookCollection()
        assert len(col.books) == 1
        assert col.books[0].title == "1984"

    def test_corrupted_json_gives_empty_collection_with_warning(
        self, tmp_path, monkeypatch, capsys
    ):
        data_file = tmp_path / "data.json"
        data_file.write_text("not valid json {{")
        monkeypatch.setattr(books, "DATA_FILE", str(data_file))
        col = BookCollection()
        assert col.books == []
        assert "Warning" in capsys.readouterr().out

    def test_malformed_records_give_empty_collection_with_warning(
        self, tmp_path, monkeypatch, capsys
    ):
        """JSON is valid but records are missing required Book fields."""
        data_file = tmp_path / "data.json"
        data_file.write_text(json.dumps([{"wrong_field": "value"}]))
        monkeypatch.setattr(books, "DATA_FILE", str(data_file))
        col = BookCollection()
        assert col.books == []
        assert "Warning" in capsys.readouterr().out

    def test_reload_discards_unsaved_in_memory_changes(self, collection):
        collection.books.append(Book("Ghost", "Nobody", 2000))
        assert len(collection.books) == 1
        collection.load_books()  # reload from disk
        assert collection.books == []

    def test_read_flag_preserved_after_load(self, collection):
        collection.add_book("Dune", "Frank Herbert", 1965)
        collection.mark_as_read("Dune")
        fresh = BookCollection()
        book = fresh.find_book_by_title("Dune")
        assert book.read is True


# ---------------------------------------------------------------------------
# save_books
# ---------------------------------------------------------------------------

class TestSaveBooks:
    """BookCollection.save_books — atomic write and failure handling."""

    def test_raises_book_storage_error_on_os_failure(self, collection, monkeypatch):
        def boom(*args, **kwargs):
            raise OSError("disk full")
        monkeypatch.setattr("tempfile.NamedTemporaryFile", boom)
        with pytest.raises(BookStorageError):
            collection.save_books()

    def test_storage_error_message_contains_filename(self, collection, monkeypatch):
        monkeypatch.setattr("tempfile.NamedTemporaryFile", lambda *a, **kw: (_ for _ in ()).throw(OSError("nope")))
        with pytest.raises(BookStorageError, match="data.json"):
            collection.save_books()


# ---------------------------------------------------------------------------
# add_book — validation
# ---------------------------------------------------------------------------

class TestAddBookValidation:
    """add_book raises BookValidationError for invalid inputs."""

    @pytest.mark.parametrize("title", ["", "   ", "\t", "\n"])
    def test_empty_or_whitespace_title_raises(self, collection, title):
        with pytest.raises(BookValidationError, match="Title"):
            collection.add_book(title, "Author", 2000)

    @pytest.mark.parametrize("author", ["", "   ", "\t"])
    def test_empty_or_whitespace_author_raises(self, collection, author):
        with pytest.raises(BookValidationError, match="Author"):
            collection.add_book("Valid Title", author, 2000)

    @pytest.mark.parametrize("year", [-1, -100, 2101, 9999])
    def test_out_of_range_year_raises(self, collection, year):
        with pytest.raises(BookValidationError, match="Year"):
            collection.add_book("Title", "Author", year)

    @pytest.mark.parametrize("year", [1, 2, 2099, 2100])
    def test_boundary_years_are_valid(self, collection, year):
        book = collection.add_book("Title", "Author", year)
        assert book.year == year

    def test_year_zero_is_valid(self, collection):
        book = collection.add_book("Unknown Year", "Author", 0)
        assert book.year == 0

    def test_validation_error_does_not_mutate_collection(self, collection):
        with pytest.raises(BookValidationError):
            collection.add_book("", "Author", 2000)
        assert collection.books == []


# ---------------------------------------------------------------------------
# add_book — happy path and persistence
# ---------------------------------------------------------------------------

class TestAddBook:
    """add_book return value, defaults, and disk persistence."""

    def test_returns_book_instance(self, collection):
        result = collection.add_book("1984", "George Orwell", 1949)
        assert isinstance(result, Book)

    def test_returned_book_has_correct_fields(self, collection):
        book = collection.add_book("1984", "George Orwell", 1949)
        assert book.title == "1984"
        assert book.author == "George Orwell"
        assert book.year == 1949

    def test_read_defaults_to_false(self, collection):
        book = collection.add_book("1984", "George Orwell", 1949)
        assert book.read is False

    def test_book_appears_in_collection(self, collection):
        collection.add_book("1984", "George Orwell", 1949)
        assert len(collection.books) == 1

    def test_multiple_books_can_be_added(self, collection):
        collection.add_book("1984", "George Orwell", 1949)
        collection.add_book("Dune", "Frank Herbert", 1965)
        assert len(collection.books) == 2

    def test_persisted_to_disk(self, collection):
        collection.add_book("1984", "George Orwell", 1949)
        fresh = BookCollection()
        assert len(fresh.books) == 1
        assert fresh.books[0].title == "1984"

    def test_rollback_on_save_failure(self, collection, monkeypatch):
        monkeypatch.setattr(collection, "save_books", lambda: (_ for _ in ()).throw(BookStorageError("fail")))
        with pytest.raises(BookStorageError):
            collection.add_book("1984", "George Orwell", 1949)
        assert collection.books == []


# ---------------------------------------------------------------------------
# list_books
# ---------------------------------------------------------------------------

class TestListBooks:
    """BookCollection.list_books — returns in-memory book list."""

    def test_empty_collection_returns_empty_list(self, collection):
        assert collection.list_books() == []

    def test_returns_all_added_books(self, populated_collection):
        result = populated_collection.list_books()
        assert len(result) == 3

    def test_returns_same_reference_as_internal_list(self, collection):
        assert collection.list_books() is collection.books


# ---------------------------------------------------------------------------
# find_book_by_title
# ---------------------------------------------------------------------------

class TestFindBookByTitle:
    """BookCollection.find_book_by_title — lookup and case-insensitivity."""

    def test_finds_existing_book(self, populated_collection):
        book = populated_collection.find_book_by_title("1984")
        assert book is not None
        assert book.author == "George Orwell"

    def test_returns_none_when_not_found(self, collection):
        assert collection.find_book_by_title("Nonexistent") is None

    @pytest.mark.parametrize("query", ["dune", "DUNE", "Dune", "dUnE"])
    def test_case_insensitive_match(self, populated_collection, query):
        book = populated_collection.find_book_by_title(query)
        assert book is not None
        assert book.title == "Dune"

    def test_returns_correct_book_object(self, populated_collection):
        book = populated_collection.find_book_by_title("Dune")
        assert book.year == 1965


# ---------------------------------------------------------------------------
# mark_as_read
# ---------------------------------------------------------------------------

class TestMarkAsRead:
    """BookCollection.mark_as_read — state, persistence, and errors."""

    def test_sets_read_flag(self, populated_collection):
        populated_collection.mark_as_read("1984")
        book = populated_collection.find_book_by_title("1984")
        assert book.read is True

    def test_returns_none(self, populated_collection):
        result = populated_collection.mark_as_read("1984")
        assert result is None

    @pytest.mark.parametrize("title", ["dune", "DUNE", "dUnE"])
    def test_case_insensitive(self, populated_collection, title):
        populated_collection.mark_as_read(title)
        book = populated_collection.find_book_by_title("Dune")
        assert book.read is True

    def test_raises_book_not_found_error(self, collection):
        with pytest.raises(BookNotFoundError):
            collection.mark_as_read("No Such Book")

    def test_error_message_contains_title(self, collection):
        with pytest.raises(BookNotFoundError, match="Ghost"):
            collection.mark_as_read("Ghost")

    def test_persisted_to_disk(self, populated_collection):
        populated_collection.mark_as_read("1984")
        fresh = BookCollection()
        assert fresh.find_book_by_title("1984").read is True

    def test_rollback_on_save_failure(self, populated_collection, monkeypatch):
        monkeypatch.setattr(
            populated_collection, "save_books",
            lambda: (_ for _ in ()).throw(BookStorageError("fail"))
        )
        with pytest.raises(BookStorageError):
            populated_collection.mark_as_read("1984")
        assert populated_collection.find_book_by_title("1984").read is False


# ---------------------------------------------------------------------------
# remove_book
# ---------------------------------------------------------------------------

class TestRemoveBook:
    """BookCollection.remove_book — deletion, persistence, and errors."""

    def test_removes_book_from_collection(self, populated_collection):
        populated_collection.remove_book("1984")
        assert populated_collection.find_book_by_title("1984") is None

    def test_returns_none(self, populated_collection):
        result = populated_collection.remove_book("1984")
        assert result is None

    def test_other_books_unaffected(self, populated_collection):
        populated_collection.remove_book("1984")
        assert len(populated_collection.books) == 2

    @pytest.mark.parametrize("title", ["dune", "DUNE", "dUnE"])
    def test_case_insensitive(self, populated_collection, title):
        populated_collection.remove_book(title)
        assert populated_collection.find_book_by_title("Dune") is None

    def test_raises_book_not_found_error(self, collection):
        with pytest.raises(BookNotFoundError):
            collection.remove_book("No Such Book")

    def test_error_message_contains_title(self, collection):
        with pytest.raises(BookNotFoundError, match="Ghost"):
            collection.remove_book("Ghost")

    def test_persisted_to_disk(self, populated_collection):
        populated_collection.remove_book("1984")
        fresh = BookCollection()
        assert fresh.find_book_by_title("1984") is None

    def test_rollback_on_save_failure(self, populated_collection, monkeypatch):
        monkeypatch.setattr(
            populated_collection, "save_books",
            lambda: (_ for _ in ()).throw(BookStorageError("fail"))
        )
        with pytest.raises(BookStorageError):
            populated_collection.remove_book("1984")
        assert populated_collection.find_book_by_title("1984") is not None


# ---------------------------------------------------------------------------
# find_by_author
# ---------------------------------------------------------------------------

class TestFindByAuthor:
    """BookCollection.find_by_author — filtering by author name."""

    def test_returns_matching_books(self, populated_collection):
        result = populated_collection.find_by_author("Frank Herbert")
        assert len(result) == 2

    def test_returns_empty_list_when_no_match(self, populated_collection):
        result = populated_collection.find_by_author("Unknown Author")
        assert result == []

    @pytest.mark.parametrize("query", ["frank herbert", "FRANK HERBERT", "Frank Herbert"])
    def test_case_insensitive(self, populated_collection, query):
        result = populated_collection.find_by_author(query)
        assert len(result) == 2

    def test_single_match(self, populated_collection):
        result = populated_collection.find_by_author("George Orwell")
        assert len(result) == 1
        assert result[0].title == "1984"

    def test_returns_correct_book_objects(self, populated_collection):
        result = populated_collection.find_by_author("Frank Herbert")
        titles = {b.title for b in result}
        assert titles == {"Dune", "Dune Messiah"}

    def test_empty_collection_returns_empty_list(self, collection):
        assert collection.find_by_author("Anyone") == []


# ---------------------------------------------------------------------------
# get_stats (via BookCollection.get_stats)
# ---------------------------------------------------------------------------

class TestCollectionGetStats:
    """BookCollection.get_stats delegates correctly to module-level get_stats."""

    def test_returns_bookstats_instance(self, populated_collection):
        assert isinstance(populated_collection.get_stats(), BookStats)

    def test_totals_match_collection_size(self, populated_collection):
        stats = populated_collection.get_stats()
        assert stats.total == 3

    def test_read_count_after_marking(self, populated_collection):
        populated_collection.mark_as_read("1984")
        stats = populated_collection.get_stats()
        assert stats.read == 1
        assert stats.unread == 2

    def test_empty_collection_stats(self, collection):
        stats = collection.get_stats()
        assert stats.total == 0
        assert stats.oldest is None
        assert stats.newest is None
