"""Initialize AttendSense fog SQLite schema."""

from config import DB_PATH
from db import AttendSenseDB


def main() -> None:
    db = AttendSenseDB(DB_PATH)
    db.init_db()
    print(f"Initialized database at {DB_PATH}")


if __name__ == "__main__":
    main()
