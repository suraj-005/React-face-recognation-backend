import datetime
import os
import pickle
import shutil
import time
import uuid
import psycopg2
import cv2
import face_recognition
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_cors import cross_origin
app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})


ATTENDANCE_LOG_DIR = '.\\logs'
DB_PATH = '.\\db'

for dir_ in [ATTENDANCE_LOG_DIR, DB_PATH]:
    if not os.path.exists(dir_):
        os.mkdir(dir_)


@app.route('/login', methods=['POST'])
@cross_origin()
def login():
    file = request.files['file']
    file.filename = f"{uuid.uuid4()}.png"
    file.save(file.filename)

    user_name, match_status = recognize(cv2.imread(file.filename))

    if match_status:
        epoch_time = time.time()
        date = time.strftime('%Y%m%d', time.localtime(epoch_time))
        emp_code = user_name.split('_')
        try:
            connection = psycopg2.connect(
                dbname="PMS_UAT09102023",
                user="postgres",
                password="root",
                host="localhost",
                port="5432"
            )

            # Create a cursor
            cursor = connection.cursor()

            # Execute SQL queries here
            try:
                # Execute a simple query
                cursor.execute("SELECT * FROM mst_employee WHERE emp_code = %s", (emp_code[0],))
                # Fetch all the rows
                rows = cursor.fetchall()

                for row in rows:
                    print(row)

            except psycopg2.Error as e:
                print("Error executing SQL query.")
                print(e)

        except psycopg2.Error as e:
            print("Unable to connect to the database.")
            print(e)

        finally:
            # Close the cursor and connection in a finally block
            if cursor:
                cursor.close()
            if connection:
                connection.close()
            # Ensure that the directories exist
            if not os.path.exists(ATTENDANCE_LOG_DIR):
                os.makedirs(ATTENDANCE_LOG_DIR)

        date_directory = os.path.join(ATTENDANCE_LOG_DIR, date)

        if not os.path.exists(date_directory):
            os.makedirs(date_directory)

        # Now, open the file for appending
        with open(os.path.join(date_directory, 'attendance.csv'), 'a') as f:
            f.write('{},{},{}\n'.format(user_name, datetime.datetime.now(), 'IN'))

        os.remove(file.filename)
    return jsonify({'user': user_name, 'match_status': match_status, 'rows':rows})


@app.route('/logout', methods=['POST'])
@cross_origin()
def logout():
    file = request.files['file']
    file.filename = f"{uuid.uuid4()}.png"
    file.save(file.filename)

    user_name, match_status = recognize(cv2.imread(file.filename))

    if match_status:
        epoch_time = time.time()
        date = time.strftime('%Y%m%d', time.localtime(epoch_time))
        # Ensure that the directories exist
        if not os.path.exists(ATTENDANCE_LOG_DIR):
            os.makedirs(ATTENDANCE_LOG_DIR)

        date_directory = os.path.join(ATTENDANCE_LOG_DIR, date)

        if not os.path.exists(date_directory):
            os.makedirs(date_directory)

        # Now, open the file for appending
        with open(os.path.join(date_directory, 'attendance.csv'), 'a') as f:
            f.write('{},{},{}\n'.format(user_name, datetime.datetime.now(), 'OUT'))

        os.remove(file.filename)

    return jsonify({'user': user_name, 'match_status': match_status})


@app.route('/register_new_user', methods=['POST'])
@cross_origin()
def register_new_user():
    file = request.files['file']
    if request.headers['Content-Type'] == 'application/json':
            data = request.get_json()
            employee_code = data.get('employeeCode')
            employee_name = data.get('employeeName')
            mobile_no = data.get('mobileNo')
            adhar_no = data.get('adharNo')
            address = data.get('address')
            joining_date = data.get('joiningDate')
            retirement_date = data.get('retirementDate')
            current_address = data.get('currentAddress')
    else:
            employee_code = request.form.get('employeeCode')
            employee_name = request.form.get('employeeName')
            mobile_no = request.form.get('mobileNo')
            adhar_no = request.form.get('adharNo')
            address = request.form.get('address')
            joining_date = request.form.get('joiningDate')
            retirement_date = request.form.get('retirementDate')
            current_address = request.form.get('currentAddress')

    file.filename = f"{uuid.uuid4()}.png"
    file.save(file.filename)

    # Construct the full path for the pickle file
    pickle_file_name=employee_code+"_"+employee_name
    print(pickle_file_name)
    pickle_file_path = os.path.join(DB_PATH, '{}.pickle'.format(pickle_file_name))

    # Check if the directory exists and create it if not
    os.makedirs(os.path.dirname(pickle_file_path), exist_ok=True)

    embeddings = face_recognition.face_encodings(cv2.imread(file.filename))
    with open(pickle_file_path, 'wb') as file_:
        pickle.dump(embeddings, file_)

    os.remove(file.filename)

    return jsonify({'registration_status': 200})

@app.route('/get_attendance_logs', methods=['GET'])
@cross_origin()
def get_attendance_logs():
    filename = 'out.zip'
    shutil.make_archive(filename[:-4], 'zip', ATTENDANCE_LOG_DIR)
    return send_from_directory('.', filename, as_attachment=True)

@app.route('/', methods=['GET'])
@cross_origin()
def helloWorld():
    return "Hello World"

@app.route('/fetchEmployeeByEmpCode', methods=['GET'])
@cross_origin()
def fetchEmployeeByEmpCode():
    employee_code = request.args.get('employeeCode')
    try:
        connection = psycopg2.connect(
            dbname="PMS_UAT09102023",
            user="postgres",
            password="root",
            host="localhost",
            port="5432"
        )

        # Create a cursor
        cursor = connection.cursor()

        # Execute SQL queries here
        try:
            # Execute a simple query
            cursor.execute("SELECT * FROM mst_employee WHERE emp_code = %s", (employee_code,))
            # Fetch all the rows
            rows = cursor.fetchall()

        except psycopg2.Error as e:
            print("Error executing SQL query.")
            print(e)

    except psycopg2.Error as e:
        print("Unable to connect to the database.")
        print(e)

    finally:
        # Close the cursor and connection in a finally block
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return jsonify(rows)

def recognize(img):
    embeddings_unknown = face_recognition.face_encodings(img)

    if len(embeddings_unknown) == 0:
        return 'no_persons_found', False

    embeddings_unknown = embeddings_unknown[0]

    best_match_score = 0
    best_match_name = 'unknown_person'

    db_dir = sorted([j for j in os.listdir(DB_PATH) if j.endswith('.pickle')])

    for pickle_file in db_dir:
        path_ = os.path.join(DB_PATH, pickle_file)

        with open(path_, 'rb') as file:
            loaded_data = pickle.load(file)

        if isinstance(loaded_data, list) and len(loaded_data) > 0:
            embeddings = loaded_data[0]

            match_scores = face_recognition.face_distance([embeddings], embeddings_unknown)
            current_match_score = 1 - match_scores[0]  # Convert distance to a similarity score
            print(match_scores)
            if current_match_score > best_match_score:
                best_match_score = current_match_score
                best_match_name = pickle_file[:-7]  # Remove the '.pickle' extension
            print(best_match_name)
    # Decide based on the best match score
    if best_match_score >= 0.50:  # You can set a threshold for recognition accuracy
        return best_match_name, True
    else:
        return 'unknown_person', False

@app.route('/save_record', methods=['POST'])
@cross_origin()
def save_record():
    if request.headers['Content-Type'] == 'application/json':
            data = request.get_json()
            employee_code = data.get('employeeCode')
            employee_name = data.get('employeeName')
            mobile_no = data.get('mobileNo')
            adhar_no = data.get('adharNo')
            address = data.get('address')
            joining_date = data.get('joiningDate')
            retirement_date = data.get('retirementDate')
            current_address = data.get('currentAddress')
    else:
            employee_code = request.form.get('employeeCode')
            employee_name = request.form.get('employeeName')
            mobile_no = request.form.get('mobileNo')
            adhar_no = request.form.get('adharNo')
            address = request.form.get('address')
            joining_date = request.form.get('joiningDate')
            retirement_date = request.form.get('retirementDate')
            current_address = request.form.get('currentAddress')
    connection = psycopg2.connect(
        dbname="PMS_UAT09102023",
        user="postgres",
        password="root",
        host="localhost",
        port="5432"
    )

    # Create a cursor
    cursor = connection.cursor()

    insert_query = "INSERT INTO verification_transaction (emp_code, emp_name,created_date) VALUES (%s, %s, %s)"
    data_to_insert = (employee_code, employee_name,datetime.datetime.now())

    try:
        cursor.execute(insert_query, data_to_insert)
        connection.commit()
        print("Data inserted successfully!")

    except psycopg2.Error as e:
        print("Error inserting data into the table.")
        print(e)

    finally:
        # Close the cursor and connection
        cursor.close()
        connection.close()
    return jsonify({'save_status': 200})

if __name__ == "__main__":
    app.run()
