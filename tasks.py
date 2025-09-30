import smtplib
from email.mime.text import MIMEText
from flask import Flask
import sqlite3
from datetime import datetime, date
from planora import calculate_next_date

app = Flask(__name__)
app.secret_key= "suat"
DATABASE = "planora.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def guncelle_gorevler():
    bugun = date.today()
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("Select * From habits WHERE start_date = ?",(bugun,))
        tasks = cursor.fetchall()
        for i in tasks:
            frequency = i["frequency"]
            days = i["days"]
            id = i["id"]
            eski = i["date"]
            son = i["last_completed_date"]
            tarih = calculate_next_date(frequency, days, eski)
            start_date = calculate_next_date(frequency, days, tarih)
            cursor.execute("UPDATE habits SET start_date = ? ,date = ?, streak_count = 0, level = 'E' WHERE id = ?",(start_date,tarih,id))
        conn.commit()
        conn.close()
def mail_gonder():
    bugun = date.today()
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, username FROM users WHERE mail_notifications = 1")
        users = cursor.fetchall()
        for user in users:
            user_id = user["id"]
            email = user["email"]
            user_name = user["username"]
            cursor.execute(
                "Select * From tasks where user_id = ? and ((date = ?) OR (start_date <= ? AND end_date >= ?) OR end_date IS NULL) and is_completed IS NULL",
                (user_id, bugun, bugun, bugun)
            )
            tasks = cursor.fetchall()
            cursor.execute("Select * From habits where user_id = ? and date = ?",(user_id, bugun))
            habits = cursor.fetchall()
            gorevler = tasks + habits

            gorevler_text = "\n".join([f"- {t['title']}: {t['description']}" for t in gorevler])
            mesaj_icerik = f"Merhaba {user_name},\n\nBugünkü görevlerin:\n\n{gorevler_text}"

            mesaj = MIMEText(mesaj_icerik, "plain", "utf-8")
            mesaj["Subject"] = f"Planora - {bugun} Görevlerin"
            mesaj["From"] = "planora321@gmail.com"
            mesaj["To"] = email

            try:
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login("planora321@gmail.com", "mdtrjcskfnvzlqxt")
                    server.send_message(mesaj)
                print(f"[OK] Mail gönderildi -> {email}")
            except Exception as e:
                print(f"[HATA] Mail gönderilemedi -> {email} | {e}")

        conn.close()

if __name__ == "__main__":
    guncelle_gorevler()
    mail_gonder()