from flask import Flask, send_file
import os
from datetime import datetime, timezone
import uuid
import csv
import zipfile
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


app = Flask(__name__)
report_data = []

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "test"
COLLECTION_NAME = "test_render"

doc = {
    "test": "insert",
    "timestamp": datetime.now(timezone.utc).isoformat()
}


MONGO_URI = os.getenv("MONGO_URI") or "mongodb+srv://admin:admin@cluster0.tmhpxbi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


# ----------------------
# TESTY
# ----------------------

def log_result(test_name, status, message):
    print(f"{'✅' if status == 'PASS' else '❌'} [{test_name}] {message}")
    report_data.append({
        "test": test_name,
        "status": status,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    })


def test_connection(client):
    try:
        client.admin.command('ping')
        log_result("TEST 1", "PASS", "Połączenie z MongoDB powiodło się.")
        return True
    except ConnectionFailure as e:
        log_result("TEST 1", "FAIL", f"Błąd połączenia: {e}")
        return False


def test_insert_and_read(collection):
    doc_id = str(uuid.uuid4())
    test_doc = {"_id": doc_id, "test": "insert", "status": "ok"}
    collection.insert_one(test_doc)
    retrieved = collection.find_one({"_id": doc_id})
    if retrieved:
        log_result("TEST 2", "PASS", "Insert i odczyt dokumentu powiodły się.")
    else:
        log_result("TEST 2", "FAIL", "Insert lub odczyt dokumentu nie powiódł się.")


def test_empty_collection_behavior(collection):
    collection.delete_many({})
    results = list(collection.find({}))
    if len(results) == 0:
        log_result("TEST 3", "PASS", "Kolekcja pusta – brak danych jak oczekiwano.")
    else:
        log_result("TEST 3", "FAIL", f"Kolekcja nie jest pusta: {results}")


def test_schema_validation(collection):
    test_doc = {"name": "Jan", "age": 30}
    try:
        collection.insert_one(test_doc)
        log_result("TEST 4", "PASS", "Dokument zgodny ze schematem (jeśli ustawiony).")
    except Exception as e:
        log_result("TEST 4", "FAIL", f"Wstawienie niezgodne ze schematem: {e}")


# ----------------------
# RAPORTY
# ----------------------

def save_report_csv(filename="raport.csv"):
    with open(filename, "w", newline='', encoding="utf-8") as csvfile:
        fieldnames = ["Test", "Status", "Komunikat", "Czas"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in report_data:
            writer.writerow({
                "Test": row["test"],
                "Status": "Sukces" if row["status"] == "PASS" else "Błąd",
                "Komunikat": row["message"],
                "Czas": row["timestamp"]
            })


def save_report_html(filename="raport.html"):
    with open(filename, "w", encoding="utf-8") as htmlfile:
        htmlfile.write("<html><head><meta charset='utf-8'><title>Raport testów MongoDB</title></head><body>")
        htmlfile.write("<h1>Raport testów MongoDB</h1><table border='1'>")
        htmlfile.write("<tr><th>Test</th><th>Status</th><th>Komunikat</th><th>Czas</th></tr>")
        for row in report_data:
            color = "#c8e6c9" if row["status"] == "PASS" else "#ffcdd2"
            htmlfile.write(f"<tr bgcolor='{color}'>")
            htmlfile.write(
                f"<td>{row['test']}</td><td>{'Sukces' if row['status'] == 'PASS' else 'Błąd'}</td><td>{row['message']}</td><td>{row['timestamp']}</td>")
            htmlfile.write("</tr>")
        htmlfile.write("</table></body></html>")


def zip_reports(zip_filename="raport_mongodb.zip"):
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write("raport.csv")
        zipf.write("raport.html")


# ----------------------
# FLASK ROUTE
# ----------------------

@app.route("/generuj-raport")
def generate_report():
    report_data.clear()
    if not MONGO_URI:
        return "Brak zmiennej środowiskowej MONGO_URI", 500

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)

    if test_connection(client):
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        test_empty_collection_behavior(collection)
        test_insert_and_read(collection)
        test_schema_validation(collection)

        save_report_csv()
        save_report_html()
        zip_reports()

        return send_file("raport_mongodb.zip", as_attachment=True)
    else:
        return "Błąd połączenia z MongoDB", 500


@app.route("/")
def home():
    return "<h2>MongoDB Tester Flask API</h2><p>Wejdź na <a href='/generuj-raport'>/generuj-raport</a> aby pobrać raport ZIP.</p>"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
