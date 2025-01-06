from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import sqlite3
import os

app = Flask(__name__)

DATABASE = 'courses.db'

# Helper function to connect to the database
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Allows dictionary-like access to rows
    return conn

# Helper function to check for time conflicts
def has_time_conflict(time1, days1, time2, days2):
    """Check if two courses overlap in time and days"""
    if time1 == "TBA" or time2 == "TBA":
        return False  # Skip conflict check for TBA courses

    # Check if the days overlap
    for day in days1:
        if day in days2:
            # Parse start and end times
            start1, end1 = map(lambda t: int(t.replace(":", "")), time1.split("-"))
            start2, end2 = map(lambda t: int(t.replace(":", "")), time2.split("-"))
            
            # Check for overlap
            if not (end1 <= start2 or end2 <= start1):
                return True

    return False

@app.route('/')
def home():
    """Homepage with navigation links"""
    return render_template('index.html', title='Home')

@app.route('/courses', methods=['GET'])
def courses():
    """View and search courses."""
    query = request.args.get('query', '').strip()
    conn = get_db_connection()
    try:
        if query:
            courses = conn.execute('''
                SELECT * FROM Courses
                WHERE courseCode LIKE ? OR courseName LIKE ?
            ''', (f'%{query}%', f'%{query}%')).fetchall()
        else:
            courses = conn.execute('SELECT * FROM Courses').fetchall()

        return render_template(
            'classes.html',  # Using classes.html for the courses display
            title='View Courses', 
            courses=courses, 
            query=query
        )
    finally:
        conn.close()


@app.route('/courses/search', methods=['GET'])
def search_courses():
    """Search for courses by name or code"""
    query = request.args.get('query', '')
    conn = get_db_connection()
    courses = conn.execute(
        'SELECT * FROM Courses WHERE courseCode LIKE ? OR courseName LIKE ?',
        (f'%{query}%', f'%{query}%')
    ).fetchall()
    conn.close()
    return render_template('search_results.html', title='Search Results', courses=courses, query=query)

@app.route('/schedule', methods=['GET'])
def view_schedule():
    """View the user's schedule"""
    conn = get_db_connection()
    schedule = conn.execute('''
        SELECT s.id AS scheduleID, c.courseCode, c.courseName, c.instructor, c.time, c.days
        FROM Schedule s
        JOIN Courses c ON s.courseID = c.id
    ''').fetchall()
    conn.close()
    return render_template('schedule.html', title='Your Schedule', schedule=schedule)

@app.route('/create-schedule', methods=['GET', 'POST'])
def create_schedule():
    """Create or modify the user's schedule"""
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            course_id = request.form.get('courseID')

            # Get details of the selected course
            selected_course = conn.execute('SELECT * FROM Courses WHERE id = ?', (course_id,)).fetchone()
            if not selected_course:
                return render_template(
                    'create_schedule.html', 
                    title='Create Schedule', 
                    error="Course not found.", 
                    courses=conn.execute('SELECT * FROM Courses').fetchall()
                )

            # Check if the specific course section is already in the schedule
            existing_section = conn.execute(
                'SELECT * FROM Schedule WHERE courseID = ?', 
                (course_id,)
            ).fetchone()
            if existing_section:
                return render_template(
                    'create_schedule.html', 
                    title='Create Schedule', 
                    error="This class section is already in your schedule.", 
                    courses=conn.execute('SELECT * FROM Courses').fetchall()
                )

            # Restrict adding child sections without parent lecture
            if selected_course['type'] in ['Lab', 'Discussion', 'Quiz']:
                parent_ids = selected_course['parentID'].split("/")
                parent_in_schedule = conn.execute(
                    'SELECT * FROM Schedule WHERE courseID IN ({seq})'.format(
                        seq=",".join(["?"] * len(parent_ids))
                    ),
                    parent_ids
                ).fetchone()
                if not parent_in_schedule:
                    return render_template(
                        'create_schedule.html',
                        title='Create Schedule',
                        error="You must add the parent lecture before adding this section.",
                        courses=conn.execute('SELECT * FROM Courses').fetchall()
                    )

            # Check for duplicate lecture sections
            if selected_course['type'] == 'Lecture':
                existing_lecture = conn.execute('''
                    SELECT c.*
                    FROM Schedule s
                    JOIN Courses c ON s.courseID = c.id
                    WHERE c.courseCode = ? AND c.type = 'Lecture'
                ''', (selected_course['courseCode'],)).fetchone()
                if existing_lecture:
                    return render_template(
                        'create_schedule.html',
                        title='Create Schedule',
                        error=(f"You already have a lecture for {selected_course['courseCode']} in your schedule."),
                        courses=conn.execute('SELECT * FROM Courses').fetchall()
                    )

            # Check for time conflicts
            schedule = conn.execute('''
                SELECT c.*
                FROM Schedule s
                JOIN Courses c ON s.courseID = c.id
            ''').fetchall()
            for scheduled_course in schedule:
                if has_time_conflict(
                    selected_course['time'], selected_course['days'],
                    scheduled_course['time'], scheduled_course['days']
                ):
                    conflict_message = (
                        f"Time conflict with course: {scheduled_course['courseCode']} - {scheduled_course['courseName']} "
                        f"({scheduled_course['time']} {scheduled_course['days']})"
                    )
                    return render_template(
                        'create_schedule.html',
                        title='Create Schedule',
                        error=conflict_message,
                        courses=conn.execute('SELECT * FROM Courses').fetchall()
                    )

            # Add the course to the schedule
            conn.execute('INSERT INTO Schedule (courseID) VALUES (?)', (course_id,))
            conn.commit()

            # Prompt user to add associated child sections if lecture was added
            if selected_course['type'] == 'Lecture':
                child_sections = conn.execute('''
                    SELECT * FROM Courses 
                    WHERE parentID LIKE ?
                ''', (f"%{selected_course['id']}%",)).fetchall()
                if child_sections:
                    return render_template(
                        'select_child_sections.html', 
                        title='Select Child Sections',
                        parent_course=selected_course, 
                        child_sections=child_sections
                    )

            return redirect(url_for('view_schedule'))

        # For GET request
        courses = conn.execute('SELECT * FROM Courses').fetchall()
        return render_template('create_schedule.html', title='Create Schedule', courses=courses)
    finally:
        conn.close()


@app.route('/schedule/remove/<int:schedule_id>', methods=['POST'])
def remove_from_schedule(schedule_id):
    """Remove a course from the user's schedule"""
    conn = get_db_connection()
    conn.execute('DELETE FROM Schedule WHERE id = ?', (schedule_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('view_schedule'))


def gpa_to_letter_grade(gpa):
    """Convert a GPA value to a letter grade."""
    if gpa >= 3.85:
        return 'A'
    elif gpa >= 3.50:
        return 'A-'
    elif gpa >= 3.15:
        return 'B+'
    elif gpa >= 2.85:
        return 'B'
    elif gpa >= 2.50:
        return 'B-'
    elif gpa >= 2.15:
        return 'C+'
    elif gpa >= 1.85:
        return 'C'
    elif gpa >= 1.50:
        return 'C-'
    elif gpa >= 1.15:
        return 'D+'
    elif gpa >= 0.85:
        return 'D'
    else:
        return 'F'

@app.route('/grades', methods=['GET', 'POST'])
def grades():
    """Display grade statistics for a selected course."""
    grade_files = [f.split(".")[0] for f in os.listdir('grades') if f.endswith('.txt')]

    if request.method == 'POST':
        course_code = request.form.get('courseCode')
        filepath = os.path.join('grades', f'{course_code}.txt')

        if not os.path.exists(filepath):
            return render_template('grades.html', title='Grade Distributions', courses=grade_files, error="Grade file not found.")

        # Read grades from the file
        with open(filepath, 'r') as file:
            grades = file.read().splitlines()

        # Filter and count grades
        grade_counts = {
            'A': 0, 'A-': 0, 'B+': 0, 'B': 0, 'B-': 0,
            'C+': 0, 'C': 0, 'C-': 0, 'D+': 0, 'D': 0, 'F': 0
        }
        numeric_grades = []

        grade_to_numeric = {
            'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'F': 0.0
        }

        for grade in grades:
            if grade in grade_counts:
                grade_counts[grade] += 1
                numeric_grades.append(grade_to_numeric[grade])

        # Calculate average grade
        average_gpa = round(sum(numeric_grades) / len(numeric_grades), 2) if numeric_grades else 0.0
        average_grade_letter = gpa_to_letter_grade(average_gpa)

        return render_template(
            'grades.html',
            title='Grade Distributions',
            courses=grade_files,
            selected_course=course_code,
            grade_counts=grade_counts,
            average_grade=average_grade_letter
        )

    return render_template('grades.html', title='Grade Distributions', courses=grade_files)

@app.route('/add-child-sections', methods=['POST'])
def add_child_sections():
    """Add parent lecture and required child sections to the schedule."""
    conn = get_db_connection()
    try:
        selected_sections = request.form.getlist('selectedSections')

        if not selected_sections:
            return render_template(
                'error.html',
                title="Error",
                message="You must select at least one section to add."
            )

        # Fetch the first selected section
        first_section = conn.execute('SELECT * FROM Courses WHERE id = ?', (selected_sections[0],)).fetchone()

        if not first_section:
            return render_template(
                'error.html',
                title="Error",
                message="Invalid section selected."
            )

        # Get the parent lecture IDs for the selected section
        parent_ids = first_section['parentID']
        if not parent_ids:
            return render_template(
                'error.html',
                title="Error",
                message="This section does not have associated parent information."
            )

        parent_ids = parent_ids.split("/")
        parent_lecture = conn.execute(
            'SELECT * FROM Courses WHERE id IN ({seq})'.format(seq=",".join(["?"] * len(parent_ids))),
            parent_ids
        ).fetchone()

        if not parent_lecture:
            return render_template(
                'error.html',
                title="Error",
                message="The parent lecture for this section could not be found."
            )

        # Check if the parent lecture is already in the schedule
        parent_in_schedule = conn.execute(
            'SELECT * FROM Schedule WHERE courseID = ?',
            (parent_lecture['id'],)
        ).fetchone()

        # Fetch all required child types for the parent lecture
        required_child_types = conn.execute(
            'SELECT DISTINCT type FROM Courses WHERE parentID IN ({seq})'.format(seq=",".join(["?"] * len(parent_ids))),
            parent_ids
        ).fetchall()
        required_child_types = {row['type'] for row in required_child_types}

        # Determine the types of the selected sections
        selected_types = set()
        for section_id in selected_sections:
            child_section = conn.execute('SELECT * FROM Courses WHERE id = ?', (section_id,)).fetchone()

            if not child_section:
                return render_template(
                    'error.html',
                    title="Error",
                    message="One of the selected sections could not be found."
                )

            if child_section['type'] in selected_types:
                child_sections = conn.execute(
                    'SELECT * FROM Courses WHERE parentID LIKE ?',
                    (f"%{parent_ids[0]}%",)
                ).fetchall()
                return render_template(
                    'select_child_sections.html',
                    title="Select Child Sections",
                    parent_course=parent_lecture,
                    child_sections=child_sections,
                    error=f"You can only select one {child_section['type']} section. Please try again."
                )

            selected_types.add(child_section['type'])

        # Check if any required types are missing
        missing_types = required_child_types - selected_types
        if missing_types:
            child_sections = conn.execute(
                'SELECT * FROM Courses WHERE parentID LIKE ?',
                (f"%{parent_ids[0]}%",)
            ).fetchall()
            return render_template(
                'select_child_sections.html',
                title="Select Child Sections",
                parent_course=parent_lecture,
                child_sections=child_sections,
                error=f"The following types of sections are required but not selected: {', '.join(missing_types)}."
            )

        # If parent lecture is not in the schedule, ensure it is added
        if not parent_in_schedule:
            conn.execute('INSERT INTO Schedule (courseID) VALUES (?)', (parent_lecture['id'],))

        # Add the selected sections to the schedule
        for section_id in selected_sections:
            conn.execute('INSERT INTO Schedule (courseID) VALUES (?)', (section_id,))

        conn.commit()
        return redirect(url_for('view_schedule'))
    finally:
        conn.close()



@app.route('/calendar')
def calendar():
    """Weekly calendar view."""
    conn = get_db_connection()
    try:
        schedule = conn.execute('''
            SELECT c.courseCode, c.courseName, c.time, c.days
            FROM Schedule s
            JOIN Courses c ON s.courseID = c.id
        ''').fetchall()

        events = []
        for row in schedule:
            time_range = row['time'].split('-')
            if len(time_range) != 2:
                continue  # Skip if the time format is invalid

            start_time = time_range[0]
            end_time = time_range[1]
            try:
                start_hour = int(start_time.split(':')[0])
                end_hour = int(end_time.split(':')[0])
            except ValueError:
                continue  # Skip if start or end time isn't valid

            events.append({
                'courseCode': row['courseCode'],
                'courseName': row['courseName'],
                'time': row['time'],
                'days': row['days'],  # E.g., "MW"
                'start_hour': start_hour,
                'end_hour': end_hour,
            })

        return render_template('calendar.html', title='Weekly Calendar', events=events)
    finally:
        conn.close()

if __name__ == '__main__':
    # Ensure the database file exists
    if not os.path.exists(DATABASE):
        print(f"Error: Database file '{DATABASE}' not found.")
        exit(1)
    app.run(debug=True)