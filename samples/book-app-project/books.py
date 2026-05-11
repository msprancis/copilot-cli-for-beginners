import json
import os
import tempfile
from dataclasses import dataclass, asdict
from typing import List, Optional

DATA_FILE = "data.json"


@dataclass
class Book:
    title: str
    author: str
    year: int
    read: bool = False


class BookCollection:
    def __init__(self):
        self.books: List[Book] = []
        self.load_books()

    def load_books(self):
        """Load books from the JSON file if it exists."""
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                self.books = [Book(**b) for b in data]
        except FileNotFoundError:
            self.books = []
        except json.JSONDecodeError:
            print("Warning: data.json is corrupted. Starting with empty collection.")
            self.books = []

    def save_books(self):
        """Save the current book collection to JSON using an atomic write."""
        dir_name = os.path.dirname(os.path.abspath(DATA_FILE))
        try:
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, suffix=".tmp") as tmp:
                json.dump([asdict(b) for b in self.books], tmp, indent=2)
                tmp_path = tmp.name
            os.replace(tmp_path, DATA_FILE)
        except OSError as e:
            raise IOError(f"Failed to save books to {DATA_FILE}: {e}") from e

    def add_book(self, title: str, author: str, year: int) -> Book:
        book = Book(title=title, author=author, year=year)
        self.books.append(book)
        self.save_books()
        return book

    def list_books(self) -> List[Book]:
        return self.books

    def find_book_by_title(self, title: str) -> Optional[Book]:
        for book in self.books:
            if book.title.lower() == title.lower():
                return book
        return None

    def mark_as_read(self, title: str) -> bool:
        book = self.find_book_by_title(title)
        if book:
            book.read = True
            self.save_books()
            return True
        return False

    def remove_book(self, title: str) -> bool:
        """Remove a book by title."""
        book = self.find_book_by_title(title)
        if book:
            self.books.remove(book)
            self.save_books()
            return True
        return False

    def find_by_author(self, author: str) -> List[Book]:
        """Find all books by a given author."""
        return [b for b in self.books if b.author.lower() == author.lower()]

    def get_stats(self) -> "BookStats":
        """Return statistics for the entire collection."""
        return get_stats(self.books)


@dataclass
class BookStats:
    total: int
    read: int
    unread: int
    oldest: Optional[Book]
    newest: Optional[Book]


def get_stats(books: List[Book]) -> BookStats:
    """Return statistics for a list of books.

    Args:
        books: List of Book objects to analyse.

    Returns:
        A BookStats dataclass with total, read/unread counts,
        and the oldest and newest books by publication year.
        oldest/newest are None when the list is empty.
    """
    if not books:
        return BookStats(total=0, read=0, unread=0, oldest=None, newest=None)

    read_books = [b for b in books if b.read]
    dated = [b for b in books if b.year > 0]

    oldest = min(dated, key=lambda b: b.year) if dated else None
    newest = max(dated, key=lambda b: b.year) if dated else None

    return BookStats(
        total=len(books),
        read=len(read_books),
        unread=len(books) - len(read_books),
        oldest=oldest,
        newest=newest,
    )
