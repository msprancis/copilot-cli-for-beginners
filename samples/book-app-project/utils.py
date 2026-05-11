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
    return input("Choose an option (1-5): ").strip()


def get_book_details() -> tuple[str, str, int]:
    while not (title := input("Enter book title: ").strip()):
        print("Title cannot be empty. Please try again.")

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


def print_books(books: list[Book]) -> None:
    if not books:
        print("No books in your collection.")
        return

    print("\nYour Books:")
    for index, book in enumerate(books, start=1):
        status = "✅ Read" if book.read else "📖 Unread"
        print(f"{index}. {book.title} by {book.author} ({book.year}) - {status}")
