import os
import boto3
import pymysql
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# AWS S3 and RDS configuration
AWS_S3_BUCKET_NAME = ""
AWS_RDS_ENDPOINT = ""
AWS_RDS_PORT = 3306
AWS_RDS_DB_NAME = ""
AWS_RDS_USER = ""
AWS_RDS_PASSWORD = ""

# Initialize S3 and RDS clients using the IAM role attached to the EC2 instance
s3_client = boto3.client("s3")
rds_connection = pymysql.connect(
    host=AWS_RDS_ENDPOINT,
    user=AWS_RDS_USER,
    password=AWS_RDS_PASSWORD,
    db=AWS_RDS_DB_NAME,
    port=AWS_RDS_PORT
)

# Route to upload a file to S3 and save metadata in RDS
@app.route('/')
def home():
    return "Welcome to the app!", 200

@app.route('/favicon.ico')
def favicon():
    return '', 204  # No Content

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Secure filename and upload to S3
    filename = secure_filename(file.filename)
    try:
        s3_client.upload_fileobj(file, AWS_S3_BUCKET_NAME, filename)
    except Exception as e:
        return jsonify({"error": f"Error uploading file to S3: {str(e)}"}), 500

    # Insert metadata into RDS
    try:
        with rds_connection.cursor() as cursor:
            sql = "INSERT INTO file_metadata (filename, upload_time) VALUES (%s, %s)"
            cursor.execute(sql, (filename, datetime.now()))
            rds_connection.commit()
    except Exception as e:
        return jsonify({"error": f"Error saving metadata to RDS: {str(e)}"}), 500

    return jsonify({"message": "File uploaded successfully", "filename": filename}), 200

# Route to list files (metadata) from RDS
@app.route('/files', methods=['GET'])
def list_files():
    try:
        with rds_connection.cursor() as cursor:
            sql = "SELECT filename, upload_time FROM file_metadata"
            cursor.execute(sql)
            files = cursor.fetchall()
            file_list = [{"filename": row[0], "upload_time": str(row[1])} for row in files]
    except Exception as e:
        return jsonify({"error": f"Error fetching metadata from RDS: {str(e)}"}), 500

    return jsonify(file_list), 200

# Route to download a file from S3
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        file_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': AWS_S3_BUCKET_NAME, 'Key': filename},
            ExpiresIn=3600  # URL valid for 1 hour
        )
    except Exception as e:
        return jsonify({"error": f"Error generating file URL: {str(e)}"}), 500

    return jsonify({"file_url": file_url}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
    app.ren(debug=True)
