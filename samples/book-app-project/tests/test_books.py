import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import books
import book_app
from books import Book, BookCollection, BookStats, BookNotFoundError, get_stats


@pytest.fixture(autouse=True)
def use_temp_data_file(tmp_path, monkeypatch):
    """Use a temporary data file for each test."""
    temp_file = tmp_path / "data.json"
    temp_file.write_text("[]")
    monkeypatch.setattr(books, "DATA_FILE", str(temp_file))
    # Reset the global collection in book_app so it picks up the temp file
    monkeypatch.setattr(book_app, "collection", BookCollection())


def test_add_book():
    collection = BookCollection()
    initial_count = len(collection.books)
    collection.add_book("1984", "George Orwell", 1949)
    assert len(collection.books) == initial_count + 1
    book = collection.find_book_by_title("1984")
    assert book is not None
    assert book.author == "George Orwell"
    assert book.year == 1949
    assert book.read is False

def test_mark_book_as_read():
    collection = BookCollection()
    collection.add_book("Dune", "Frank Herbert", 1965)
    collection.mark_as_read("Dune")
    book = collection.find_book_by_title("Dune")
    assert book.read is True

def test_mark_book_as_read_invalid():
    collection = BookCollection()
    with pytest.raises(BookNotFoundError):
        collection.mark_as_read("Nonexistent Book")

def test_remove_book():
    collection = BookCollection()
    collection.add_book("The Hobbit", "J.R.R. Tolkien", 1937)
    collection.remove_book("The Hobbit")
    book = collection.find_book_by_title("The Hobbit")
    assert book is None

def test_remove_book_invalid():
    collection = BookCollection()
    with pytest.raises(BookNotFoundError):
        collection.remove_book("Nonexistent Book")


@pytest.fixture
def sample_books():
    return [
        Book(title="1984", author="George Orwell", year=1949, read=True),
        Book(title="Dune", author="Frank Herbert", year=1965, read=False),
        Book(title="The Hobbit", author="J.R.R. Tolkien", year=1937, read=False),
    ]


class TestBookStats:
    """Tests for get_stats and BookStats."""

    def test_empty_collection(self):
        stats = get_stats([])
        assert stats.total == 0
        assert stats.read == 0
        assert stats.unread == 0
        assert stats.oldest is None
        assert stats.newest is None

    def test_returns_bookstats_instance(self, sample_books):
        stats = get_stats(sample_books)
        assert isinstance(stats, BookStats)

    def test_total_count(self, sample_books):
        stats = get_stats(sample_books)
        assert stats.total == 3

    def test_read_and_unread_counts(self, sample_books):
        stats = get_stats(sample_books)
        assert stats.read == 1
        assert stats.unread == 2

    def test_all_books_read(self):
        books_list = [
            Book("A", "Author", 2000, read=True),
            Book("B", "Author", 2001, read=True),
        ]
        stats = get_stats(books_list)
        assert stats.read == 2
        assert stats.unread == 0

    def test_no_books_read(self):
        books_list = [
            Book("A", "Author", 2000, read=False),
            Book("B", "Author", 2001, read=False),
        ]
        stats = get_stats(books_list)
        assert stats.read == 0
        assert stats.unread == 2

    def test_oldest_book(self, sample_books):
        stats = get_stats(sample_books)
        assert stats.oldest.title == "The Hobbit"
        assert stats.oldest.year == 1937

    def test_newest_book(self, sample_books):
        stats = get_stats(sample_books)
        assert stats.newest.title == "Dune"
        assert stats.newest.year == 1965

    def test_single_book(self):
        book = Book("Solo", "Author", 2010, read=False)
        stats = get_stats([book])
        assert stats.total == 1
        assert stats.read == 0
        assert stats.unread == 1
        assert stats.oldest == book
        assert stats.newest == book

    def test_books_with_zero_year_excluded_from_oldest_newest(self):
        books_list = [
            Book("Unknown Year", "Author", 0, read=False),
            Book("Known Year", "Author", 2000, read=False),
        ]
        stats = get_stats(books_list)
        assert stats.oldest.title == "Known Year"
        assert stats.newest.title == "Known Year"

    def test_all_books_have_zero_year(self):
        books_list = [
            Book("A", "Author", 0, read=False),
            Book("B", "Author", 0, read=False),
        ]
        stats = get_stats(books_list)
        assert stats.oldest is None
        assert stats.newest is None
        assert stats.total == 2

    def test_collection_get_stats_integration(self):
        collection = BookCollection()
        collection.add_book("Neuromancer", "William Gibson", 1984)
        collection.add_book("Snow Crash", "Neal Stephenson", 1992)
        collection.mark_as_read("Neuromancer")
        stats = collection.get_stats()
        assert stats.total == 2
        assert stats.read == 1
        assert stats.unread == 1
        assert stats.oldest.title == "Neuromancer"
        assert stats.newest.title == "Snow Crash"

    @pytest.mark.parametrize("year,expected_oldest,expected_newest", [
        ([2000, 2010, 2005], 2000, 2010),
        ([1900, 1900, 1900], 1900, 1900),
    ])
    def test_oldest_newest_by_year(self, year, expected_oldest, expected_newest):
        books_list = [Book(f"Book{y}", "Author", y) for y in year]
        stats = get_stats(books_list)
        assert stats.oldest.year == expected_oldest
        assert stats.newest.year == expected_newest


class TestHandleRead:
    """Tests for the handle_read() CLI command handler."""

    def test_handle_read_marks_existing_book(self, monkeypatch, capsys):
        book_app.collection.add_book("Dune", "Frank Herbert", 1965)
        monkeypatch.setattr("builtins.input", lambda _: "Dune")

        book_app.handle_read()

        book = book_app.collection.find_book_by_title("Dune")
        assert book.read is True
        captured = capsys.readouterr()
        assert "marked as read" in captured.out

    def test_handle_read_reports_not_found(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "Nonexistent Book")

        book_app.handle_read()

        captured = capsys.readouterr()
        assert "not found" in captured.out
