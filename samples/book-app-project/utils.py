from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from books import Book


def print_menu() -> None:
    print("\n📚 Book Collection App")
    print("1. Add a book")
    print("2. List books")
    print("3. Mark book as read")
    print("4. Remove a book")
    print("5. Exit")


def get_user_choice() -> str:
    while True:
        choice = input("Choose an option (1-5): ").strip()
        if not choice:
            print("Please enter a number between 1 and 5.")
        elif not choice.isdigit():
            print("Invalid input. Please enter a number between 1 and 5.")
        elif choice not in {"1", "2", "3", "4", "5"}:
            print("Please choose a number between 1 and 5.")
        else:
            return choice


def get_book_details() -> tuple[str, str, int]:
    """Interactively prompt the user for book details with input validation.

    Collects three pieces of information from the user via stdin:
    - Title: must be non-empty and no longer than 200 characters.
    - Author: must be non-empty.
    - Publication year: must be an integer between 1 and 2100, or 0 to skip.

    Each field loops until valid input is provided, printing a descriptive
    error message on each failed attempt.

    Returns:
        tuple[str, str, int]: A three-element tuple containing:
            - title (str): The book's title, stripped of leading/trailing whitespace.
            - author (str): The author's name, stripped of leading/trailing whitespace.
            - year (int): The publication year, or 0 if the user chose to skip.
    """
    while True:
        title = input("Enter book title: ").strip()
        if not title:
            print("Title cannot be empty. Please try again.")
        elif len(title) > 200:
            print("Title is too long. Please keep it under 200 characters.")
        else:
            break

    while not (author := input("Enter author: ").strip()):
        print("Author cannot be empty. Please try again.")

    while True:
        year_input = input("Enter publication year (or 0 to skip): ").strip()
        try:
            year = int(year_input)
            if year == 0 or 1 <= year <= 2100:
                break
            print("Please enter a year between 1 and 2100, or 0 to skip.")
        except ValueError:
            print("Invalid year. Please enter a number.")

    return title, author, year


def print_books_by_year_range(books: list[Book], start_year: int, end_year: int) -> None:
    """Print all books published between start_year and end_year (inclusive).

    Books with a year of 0 (no year set) are excluded from results.

    Args:
        books (list[Book]): The full list of books to filter.
        start_year (int): The earliest publication year to include.
        end_year (int): The latest publication year to include.
    """
    if start_year > end_year:
        print("Start year must not be greater than end year.")
        return

    filtered = [b for b in books if b.year != 0 and start_year <= b.year <= end_year]

    if not filtered:
        print(f"No books found published between {start_year} and {end_year}.")
        return

    print(f"\nBooks published between {start_year} and {end_year}:")
    for index, book in enumerate(filtered, start=1):
        status = "✅ Read" if book.read else "📖 Unread"
        print(f"{index}. {book.title} by {book.author} ({book.year}) - {status}")


def print_books(books: list[Book], header: str = "Your Book Collection") -> None:
    """Display books in a user-friendly format.

    Args:
        books (list[Book]): The books to display.
        header (str): Heading printed above the list. Defaults to
            ``"Your Book Collection"``.
    """
    if not books:
        print("No books found.")
        return

    print(f"\n{header}:\n")
    for index, book in enumerate(books, start=1):
        status = "✅ Read" if book.read else "📖 Unread"
        print(f"{index}. {book.title} by {book.author} ({book.year}) - {status}")
    print()
