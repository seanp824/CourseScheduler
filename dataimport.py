import sqlite3

DATABASE = "courses.db"
DATASET_PATH = "Classes.txt"

SCHEMA = """
CREATE TABLE IF NOT EXISTS Courses (
    id TEXT PRIMARY KEY,
    courseCode TEXT NOT NULL,
    courseName TEXT NOT NULL,
    instructor TEXT,
    time TEXT,
    days TEXT,
    type TEXT,
    parentID TEXT
);
"""

def clear_and_import_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Drop and recreate the table
        cursor.execute("DROP TABLE IF EXISTS Courses")
        cursor.execute(SCHEMA)
        print("Recreated Courses table.")

        # Read and validate the dataset
        with open(DATASET_PATH, "r") as file:
            for line_number, line in enumerate(file, start=1):
                fields = line.strip().split(",")

                # Validate row format
                if len(fields) != 8:
                    print(f"Skipping invalid row {line_number}: {line.strip()}")
                    continue

                course_id, course_code, course_name, instructor, time, days, course_type, parent_id = fields

                # Insert into database
                try:
                    cursor.execute("""
                        INSERT INTO Courses (id, courseCode, courseName, instructor, time, days, type, parentID)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (course_id, course_code, course_name, instructor, time, days, course_type, parent_id))
                except sqlite3.IntegrityError as e:
                    print(f"Skipping duplicate or invalid row {line_number}: {e}")

        conn.commit()
        print("Data imported successfully.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clear_and_import_data()
