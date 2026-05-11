import sys
from books import BookCollection, BookNotFoundError, BookStorageError, BookValidationError
from utils import print_books


# Global collection instance
collection = BookCollection()


def handle_list():
    books = collection.list_books()
    print_books(books)


def handle_add():
    print("\nAdd a New Book\n")

    title = input("Title: ").strip()
    author = input("Author: ").strip()
    year_str = input("Year: ").strip()

    try:
        year = int(year_str) if year_str else 0
    except ValueError:
        print("\nInvalid year. Please enter a number.\n")
        return

    try:
        collection.add_book(title, author, year)
        print("\nBook added successfully.\n")
    except BookValidationError as e:
        print(f"\nError: {e}\n")
    except BookStorageError as e:
        print(f"\nCould not save book: {e}\n")


def handle_remove():
    print("\nRemove a Book\n")

    title = input("Enter the title of the book to remove: ").strip()
    try:
        collection.remove_book(title)
        print(f'\n"{title}" removed successfully.\n')
    except BookNotFoundError:
        print(f'\nBook "{title}" not found.\n')
    except BookStorageError as e:
        print(f"\nCould not save changes: {e}\n")


def handle_read():
    print("\nMark a Book as Read\n")

    title = input("Enter the title of the book to mark as read: ").strip()
    try:
        collection.mark_as_read(title)
        print(f'\n"{title}" marked as read.\n')
    except BookNotFoundError:
        print(f'\nBook "{title}" not found.\n')
    except BookStorageError as e:
        print(f"\nCould not save changes: {e}\n")


def handle_find():
    print("\nFind Books by Author\n")

    author = input("Author name: ").strip()
    books = collection.find_by_author(author)

    print_books(books)


def show_help():
    print("""
Book Collection Helper

Commands:
  list     - Show all books
  add      - Add a new book
  remove   - Remove a book by title
  read     - Mark a book as read
  find     - Find books by author
  help     - Show this help message
""")


def main():
    if len(sys.argv) < 2:
        show_help()
        return

    commands = {
        "list": handle_list,
        "add": handle_add,
        "remove": handle_remove,
        "read": handle_read,
        "find": handle_find,
        "help": show_help,
    }

    command = sys.argv[1].lower()
    handler = commands.get(command)

    if handler:
        handler()
    else:
        print("Unknown command.\n")
        show_help()


if __name__ == "__main__":
    main()
