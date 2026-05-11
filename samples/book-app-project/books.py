import json
import os
import tempfile
from dataclasses import dataclass, asdict
from typing import List, Optional

DATA_FILE = "data.json"


class BookAppError(Exception):
    """Base exception for all book-app errors.

    Catch this to handle any error raised by the book-app library
    without needing to list each subclass individually.

    Example::

        try:
            collection.add_book("", "Author", 2020)
        except BookAppError as e:
            print(f"Something went wrong: {e}")
    """


class BookStorageError(BookAppError):
    """Raised when reading or writing the data file fails.

    Wraps underlying :class:`OSError` exceptions so callers don't
    need to handle OS-level I/O errors directly.

    Example::

        try:
            collection.save_books()
        except BookStorageError as e:
            print(f"Disk error: {e}")
    """


class BookValidationError(BookAppError):
    """Raised when book data fails validation.

    Thrown by :meth:`BookCollection.add_book` when the supplied
    title, author, or year do not meet the required constraints.

    Example::

        try:
            collection.add_book("", "Author", 2020)
        except BookValidationError as e:
            print(f"Invalid input: {e}")
    """


class BookNotFoundError(BookAppError):
    """Raised when a requested book does not exist in the collection.

    Thrown by :meth:`BookCollection.mark_as_read` and
    :meth:`BookCollection.remove_book` when no book with the given
    title can be found.

    Example::

        try:
            collection.mark_as_read("Unknown Title")
        except BookNotFoundError as e:
            print(f"Not found: {e}")
    """


@dataclass
class Book:
    """A single book in the collection.

    Attributes:
        title (str): The book's title.
        author (str): The name of the book's author.
        year (int): Publication year, or ``0`` if unknown.
        read (bool): ``True`` if the book has been marked as read.

    Example::

        book = Book(title="1984", author="George Orwell", year=1949)
        print(book.title)  # "1984"
        print(book.read)   # False
    """

    title: str
    author: str
    year: int
    read: bool = False


class BookCollection:
    """Manages a persistent collection of books backed by a JSON file.

    Books are loaded from :data:`DATA_FILE` on instantiation and saved
    back after every mutating operation. All writes use an atomic
    temp-file-then-replace strategy to prevent data corruption.

    Attributes:
        books (List[Book]): The in-memory list of books. Do not mutate
            this directly; use the provided methods so persistence is
            maintained.

    Example::

        collection = BookCollection()
        collection.add_book("Dune", "Frank Herbert", 1965)
        for book in collection.list_books():
            print(book.title)
    """

    def __init__(self):
        self.books: List[Book] = []
        self.load_books()

    def load_books(self) -> None:
        """Load the book collection from :data:`DATA_FILE` into memory.

        Called automatically by :meth:`__init__`. Safe to call again to
        reload from disk, discarding any unsaved in-memory changes.

        If the file does not exist the collection starts empty. If the
        file is present but unreadable or malformed, a warning is printed
        and the collection starts empty rather than raising an exception.

        Raises:
            Nothing — all errors are caught and reported as console warnings.

        Example::

            collection = BookCollection()   # load_books() called here
            collection.load_books()         # reload from disk
        """
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                self.books = [Book(**b) for b in data]
        except FileNotFoundError:
            self.books = []
        except (json.JSONDecodeError, TypeError, KeyError):
            print("Warning: data.json is corrupted. Starting with empty collection.")
            self.books = []
        except OSError as e:
            print(f"Warning: Could not read {DATA_FILE}: {e}. Starting with empty collection.")
            self.books = []

    def save_books(self) -> None:
        """Persist the current in-memory collection to :data:`DATA_FILE`.

        Uses an atomic write: data is written to a temporary file in the
        same directory, then renamed over the target file. This prevents
        partial writes from corrupting the saved data.

        Called automatically by all mutating methods. You rarely need to
        call this directly.

        Raises:
            BookStorageError: If the temporary file cannot be created,
                written, or renamed. The temp file is cleaned up before
                the exception is re-raised.

        Example::

            collection.books.append(Book("Manual", "Author", 2024))
            collection.save_books()  # flush to disk
        """
        dir_name = os.path.dirname(os.path.abspath(DATA_FILE))
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, suffix=".tmp") as tmp:
                json.dump([asdict(b) for b in self.books], tmp, indent=2)
                tmp_path = tmp.name
            os.replace(tmp_path, DATA_FILE)
        except OSError as e:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise BookStorageError(f"Failed to save books to {DATA_FILE}: {e}") from e

    def add_book(self, title: str, author: str, year: int) -> "Book":
        """Add a new book to the collection and save it to disk.

        Validates all fields before mutating state. If the save fails,
        the in-memory list is rolled back so it stays consistent with
        the on-disk file.

        Args:
            title (str): The book's title. Must be non-empty and at most
                200 characters (enforced by :func:`get_book_details` in
                the UI layer; validation here covers programmatic callers).
            author (str): The author's name. Must be non-empty.
            year (int): Publication year between 1 and 2100, or ``0`` to
                leave the year unset.

        Returns:
            Book: The newly created :class:`Book` instance.

        Raises:
            BookValidationError: If ``title`` or ``author`` is empty, or
                if ``year`` is outside the allowed range.
            BookStorageError: If the collection cannot be saved to disk.
                The book is removed from the in-memory list before this
                exception propagates.

        Example::

            book = collection.add_book("Dune", "Frank Herbert", 1965)
            print(book.title)   # "Dune"
            print(book.read)    # False

            # Year 0 is allowed (means "unknown")
            collection.add_book("Untitled", "Unknown", 0)
        """
        if not title or not title.strip():
            raise BookValidationError("Title cannot be empty.")
        if not author or not author.strip():
            raise BookValidationError("Author cannot be empty.")
        if year != 0 and not (1 <= year <= 2100):
            raise BookValidationError(f"Year must be between 1 and 2100, or 0 to skip (got {year}).")
        book = Book(title=title, author=author, year=year)
        self.books.append(book)
        try:
            self.save_books()
        except BookStorageError:
            self.books.remove(book)
            raise
        return book

    def list_books(self) -> List["Book"]:
        """Return all books in the collection.

        Returns:
            List[Book]: A reference to the internal book list. Do not
                modify the returned list directly.

        Example::

            for book in collection.list_books():
                print(f"{book.title} — {'Read' if book.read else 'Unread'}")
        """
        return self.books

    def find_book_by_title(self, title: str) -> Optional["Book"]:
        """Find a book by its title using a case-insensitive match.

        Args:
            title (str): The title to search for. Matching is
                case-insensitive; ``"dune"`` matches ``"Dune"``.

        Returns:
            Book | None: The first matching :class:`Book`, or ``None``
                if no book with that title exists.

        Example::

            book = collection.find_book_by_title("dune")
            if book:
                print(book.author)  # "Frank Herbert"
        """
        for book in self.books:
            if book.title.lower() == title.lower():
                return book
        return None

    def mark_as_read(self, title: str) -> None:
        """Mark a book as read and save the change to disk.

        If the save fails, the ``read`` flag is restored to ``False``
        so the in-memory state stays consistent with the file on disk.

        Args:
            title (str): Title of the book to mark as read.
                Matching is case-insensitive.

        Returns:
            None

        Raises:
            BookNotFoundError: If no book with ``title`` exists in the
                collection.
            BookStorageError: If the updated collection cannot be saved.
                The ``read`` flag is rolled back before this propagates.

        Example::

            collection.add_book("Dune", "Frank Herbert", 1965)
            collection.mark_as_read("Dune")
            book = collection.find_book_by_title("Dune")
            print(book.read)  # True
        """
        book = self.find_book_by_title(title)
        if not book:
            raise BookNotFoundError(f"No book found with title '{title}'.")
        book.read = True
        try:
            self.save_books()
        except BookStorageError:
            book.read = False
            raise

    def remove_book(self, title: str) -> None:
        """Remove a book from the collection and save the change to disk.

        If the save fails, the book is re-appended to the in-memory list
        so it stays consistent with the file on disk.

        Args:
            title (str): Title of the book to remove.
                Matching is case-insensitive.

        Returns:
            None

        Raises:
            BookNotFoundError: If no book with ``title`` exists in the
                collection.
            BookStorageError: If the updated collection cannot be saved.
                The book is restored in memory before this propagates.

        Example::

            collection.add_book("The Hobbit", "J.R.R. Tolkien", 1937)
            collection.remove_book("The Hobbit")
            print(collection.find_book_by_title("The Hobbit"))  # None
        """
        book = self.find_book_by_title(title)
        if not book:
            raise BookNotFoundError(f"No book found with title '{title}'.")
        self.books.remove(book)
        try:
            self.save_books()
        except BookStorageError:
            self.books.append(book)
            raise

    def find_by_author(self, author: str) -> List["Book"]:
        """Return all books by a given author.

        Args:
            author (str): Author name to search for. Matching is
                case-insensitive.

        Returns:
            List[Book]: All books whose author matches ``author``.
                Returns an empty list if no matches are found.

        Example::

            books = collection.find_by_author("frank herbert")
            for book in books:
                print(book.title)  # "Dune", "Dune Messiah", etc.
        """
        return [b for b in self.books if b.author.lower() == author.lower()]

    def get_stats(self) -> "BookStats":
        """Return statistics for the entire collection.

        Delegates to the module-level :func:`get_stats` function.

        Returns:
            BookStats: A dataclass with ``total``, ``read``, ``unread``,
                ``oldest``, and ``newest`` fields.

        Example::

            stats = collection.get_stats()
            print(f"{stats.read}/{stats.total} books read")
            if stats.oldest:
                print(f"Oldest: {stats.oldest.title} ({stats.oldest.year})")
        """
        return get_stats(self.books)


@dataclass
class BookStats:
    """Aggregated statistics for a list of books.

    Returned by :func:`get_stats` and :meth:`BookCollection.get_stats`.

    Attributes:
        total (int): Total number of books.
        read (int): Number of books marked as read.
        unread (int): Number of books not yet read.
        oldest (Book | None): Book with the earliest publication year,
            ignoring books with ``year == 0``. ``None`` if all books
            have an unknown year or the list is empty.
        newest (Book | None): Book with the latest publication year,
            ignoring books with ``year == 0``. ``None`` if all books
            have an unknown year or the list is empty.

    Example::

        stats = get_stats(books)
        print(stats.total)          # 3
        print(stats.oldest.title)   # "The Hobbit"
    """

    total: int
    read: int
    unread: int
    oldest: Optional[Book]
    newest: Optional[Book]


def get_stats(books: List[Book]) -> BookStats:
    """Return statistics for a list of books.

    Books with ``year == 0`` are included in totals but excluded from
    ``oldest`` / ``newest`` calculations.

    Args:
        books (List[Book]): The list of :class:`Book` objects to analyse.
            May be empty.

    Returns:
        BookStats: A :class:`BookStats` instance with:

        - ``total`` — number of books in the list.
        - ``read`` — number of books where ``book.read is True``.
        - ``unread`` — ``total - read``.
        - ``oldest`` — book with the smallest ``year > 0``, or ``None``.
        - ``newest`` — book with the largest ``year > 0``, or ``None``.

    Raises:
        Nothing.

    Example::

        from books import Book, get_stats

        books = [
            Book("1984", "George Orwell", 1949, read=True),
            Book("Dune", "Frank Herbert", 1965),
        ]
        stats = get_stats(books)
        print(stats.total)          # 2
        print(stats.read)           # 1
        print(stats.oldest.title)   # "1984"
        print(stats.newest.title)   # "Dune"

        empty = get_stats([])
        print(empty.oldest)         # None
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
