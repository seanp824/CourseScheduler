import sqlite3
import random
import os

DATABASE = "courses.db"
OUTPUT_DIR = "grades"

# Define grade probabilities
GRADE_DISTRIBUTION = {
    "A": 15,
    "A-": 10,
    "B+": 15,
    "B": 20,
    "B-": 15,
    "C+": 10,
    "C": 8,
    "C-": 3,
    "D+": 2,
    "D": 1,
    "F": 1
}

def generate_random_grades(num_students):
    """Generate a list of random grades based on grade distribution."""
    grades = []
    for grade, weight in GRADE_DISTRIBUTION.items():
        grades.extend([grade] * weight)
    return [random.choice(grades) for _ in range(num_students)]

def write_grade_distributions():
    """Generate and write random grade distributions for each professor's sections."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Get distinct courses and professors
    courses = cursor.execute("""
        SELECT DISTINCT courseCode, instructor 
        FROM Courses 
        WHERE type = 'Lecture'
    """).fetchall()

    for course in courses:
        course_code, instructor = course
        file_name = f"{OUTPUT_DIR}/{course_code.replace('-', '_')}_{instructor.replace(' ', '_')}.txt"
        
        # Generate grades for a random number of students (20-100)
        num_students = random.randint(20, 100)
        grades = generate_random_grades(num_students)
        
        # Write to file
        with open(file_name, "w") as file:
            file.write("\n".join(grades))
        
        print(f"Grades for {course_code} by {instructor} written to {file_name}")

    conn.close()

if __name__ == "__main__":
    write_grade_distributions()
