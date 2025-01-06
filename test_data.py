import sqlite3

DATABASE = "courses.db"

def test_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Query the first 10 rows
        cursor.execute("SELECT * FROM Courses LIMIT 10")
        rows = cursor.fetchall()

        if rows:
            print("Here are the first 10 rows of the Courses table:")
            for row in rows:
                print(row)
        else:
            print("No data found in the Courses table.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_database()
