from flask import Flask, render_template, send_file
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime, timezone
import os, uuid, csv, zipfile

app = Flask(__name__)
report_data = []

def log_result(test_name, status, message):
    report_data.append({
        "test": test_name,
        "status": status,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    })

def run_tests():
    report_data.clear()
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        log_result("ENV", "FAIL", "Brak zmiennej środowiskowej MONGO_URI")
        return

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
    try:
        client.admin.command('ping')
        log_result("TEST 1", "PASS", "Połączenie z MongoDB powiodło się.")
    except ConnectionFailure as e:
        log_result("TEST 1", "FAIL", f"Błąd połączenia: {e}")
        return

    db = client["test"]
    collection = db["test_render"]

    collection.delete_many({})
    if not list(collection.find({})):
        log_result("TEST 2", "PASS", "Kolekcja pusta – brak danych jak oczekiwano.")
    else:
        log_result("TEST 2", "FAIL", "Kolekcja nie jest pusta.")

    doc_id = str(uuid.uuid4())
    test_doc = {"_id": doc_id, "test": "insert", "status": "ok"}
    collection.insert_one(test_doc)
    if collection.find_one({"_id": doc_id}):
        log_result("TEST 3", "PASS", "Insert i odczyt dokumentu powiodły się.")
    else:
        log_result("TEST 3", "FAIL", "Nie udało się odczytać dokumentu.")

    try:
        collection.insert_one({"name": "Jan", "age": 30})
        log_result("TEST 4", "PASS", "Dokument zgodny ze schematem (jeśli ustawiony).")
    except Exception as e:
        log_result("TEST 4", "FAIL", f"Wstawienie niezgodne ze schematem: {e}")

def save_reports():
    os.makedirs("static/raporty", exist_ok=True)
    with open("static/raporty/raport.csv", "w", newline='', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["Test", "Status", "Komunikat", "Czas"])
        writer.writeheader()
        for row in report_data:
            writer.writerow({
                "Test": row["test"],
                "Status": "Sukces" if row["status"] == "PASS" else "Błąd",
                "Komunikat": row["message"],
                "Czas": row["timestamp"]
            })

    with open("static/raporty/raport.html", "w", encoding="utf-8") as htmlfile:
        htmlfile.write(render_template("raport.html", data=report_data))

    with zipfile.ZipFile("static/raporty/raport.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write("static/raporty/raport.csv", arcname="raport.csv")
        zipf.write("static/raporty/raport.html", arcname="raport.html")

@app.route("/")
def index():
    run_tests()
    save_reports()
    return render_template("raport.html", data=report_data)

@app.route("/pobierz")
def download():
    return send_file("static/raporty/raport.zip", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
