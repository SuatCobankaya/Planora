from flask import Flask,render_template,flash,redirect,url_for,session,logging,request,jsonify
from wtforms import Form,StringField,TextAreaField,PasswordField,validators, SelectField, SelectMultipleField, widgets, BooleanField
from wtforms.validators import DataRequired
from passlib.hash import sha256_crypt
from functools import wraps
from datetime import date, datetime, timedelta
import sqlite3
# Kullanıcı Giriş Decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın.","danger")
            return redirect(url_for("login"))

    return decorated_function

def calculate_next_date(frequency, days, current_date):
    if frequency == "daily":
        return current_date + timedelta(days=1)
    elif frequency == "weekly":
        # haftalık günlerden sıradaki günü bul
        days_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
        today_weekday = current_date.weekday()  # 0 = Pazartesi
        selected_days = sorted([days_map[d] for d in days])

        for d in selected_days:
            if d > today_weekday:
                delta = d - today_weekday
                return current_date + timedelta(days=delta)
        # eğer bu haftada gün kalmadıysa → ilk seçilen güne git
        first_day = selected_days[0]
        delta = (7 - today_weekday) + first_day
        return current_date + timedelta(days=delta)
    
# Kullanıcı Kayıt Formu
class RegisterForm(Form):
    username = StringField("Kullanıcı Adı",validators=[validators.Length(min = 5,max = 35)])
    email = StringField("Email Adresi",validators=[validators.Email(message = "Lütfen Geçerli Bir Email Adresi Girin...")])
    password = PasswordField("Parola:",validators=[
        validators.DataRequired(message = "Lütfen bir parola belirleyin"),
        validators.EqualTo(fieldname = "confirm",message="Parolanız Uyuşmuyor...")
    ])
    confirm = PasswordField("Parola Doğrula")

class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

class ProfilForm(Form):
    avatar = SelectField("Avatar", choices=[
        ('jinwoo', 'Jinwoo'),
        ('miyata', 'Miyata'),
        ('peaky', 'Peaky Blinders(Erkek)'),
        ('blinder', 'Peaky Blinders(Kız)'),
        ('chaein', 'Cha Hae-in'),
        ('initial', 'İnitial D'),
        ('thor', 'Thor'),
    ])
    chekbox = BooleanField("Onayla")

class gorevForm(Form):
    title = StringField("Görev Başlığı",validators=[validators.Length(min = 5,max = 100)])
    content = TextAreaField("Görev İçeriği",validators=[validators.Length(min = 10)])
    repeat_type = SelectField("Görev Zamanı", choices=[
        ('daily', '1 gün içinde'),
        ('weekly', '1 hafta içinde'),
        ('monthly', '1 ay içinde'),
        ('suresiz', 'Süresiz'),
        ('aralikli', 'Aralıklı Tekrar'),
    ])

class HabitForm(Form):
    title = StringField("Görev Başlığı",validators=[validators.Length(min = 5,max = 100)])
    content = TextAreaField("Görev İçeriği",validators=[validators.Length(min = 10)])
    frequency = SelectField(
        "Tekrar Süresi",
        choices=[("daily", "Her Gün"), ("weekly", "Her Hafta")],
        validators=[DataRequired()]
    )
    days = SelectMultipleField(
        "Haftalık Günler",
        choices=[
            ("Mon", "Pazartesi"),
            ("Tue", "Salı"),
            ("Wed", "Çarşamba"),
            ("Thu", "Perşembe"),
            ("Fri", "Cuma"),
            ("Sat", "Cumartesi"),
            ("Sun", "Pazar"),
        ],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False)
    )

#Veritabanı Bağlantısı
app = Flask(__name__)
app.secret_key= "suat"
DATABASE = "planora.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
@login_required
def index():
   conn = get_db()
   cursor = conn.cursor()

   result = cursor.execute("Select * From users where username = ?",(session["username"],))

   data = cursor.fetchone()

   bugun = date.today()

   result4 = cursor.execute("Select * From tasks where user_id = ? and date = ? and is_completed IS NULL",(session["user_id"],bugun))

   tasks1 = cursor.fetchall()

   result3 = cursor.execute("Select * From tasks where user_id = ? and ((start_date <= ? AND end_date >= ?) OR end_date IS NULL) and is_completed IS NULL",(session["user_id"],bugun,bugun))

   tasks2 = cursor.fetchall()

   tasks = tasks1 + tasks2

   result2 = result4 + result3
   today = date.today()
   updated_tasks = []
   for task in tasks:
        # end_date alanı datetime/datetime64 olabilir, string ise dönüştürmen gerekebilir
        end_date = task["end_date"]
        if isinstance(end_date, datetime):
            end_date = end_date.date()
        days_left = (end_date - today).days if end_date else None

        # dictionary’ye yeni alan ekle
        task["days_left"] = days_left
        updated_tasks.append(task)

   cursor.execute("Select * From habits where user_id = ? and date = ? and last_completed_date != ?",(session["user_id"],bugun,bugun))

   habits = cursor.fetchall()
   conn.close()
   if result > 0 or result2 > 0:
        return render_template("index.html",data = data, tasks = updated_tasks, habits = habits)

   return render_template("index.html")

#Kayıt Olma
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("Insert into users(username,email,password) VALUES(?,?,?)",(username,email,password))
        conn.commit()

        conn.close()
        flash("Başarıyla Kayıt Oldunuz...","success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)
    
# Login İşlemi
@app.route("/login",methods =["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
       username = form.username.data
       password_entered = form.password.data
       conn = get_db()
    
       cursor = conn.cursor()

       cursor.execute("Select * From users where username = ?",(username,))

       result = cursor.fetchone()

       if result :
           data = cursor.fetchone()
           real_password = data["password"]
           if sha256_crypt.verify(password_entered,real_password):
               flash("Başarıyla Giriş Yaptınız...","success")

               session["logged_in"] = True
               session["username"] = username
               session["user_id"] = data["id"]

               return redirect(url_for("index"))
           else:
               flash("Parolanızı Yanlış Girdiniz...","danger")
               return redirect(url_for("login")) 

       else:
           flash("Böyle bir kullanıcı bulunmuyor...","danger")
           return redirect(url_for("login"))

    
    return render_template("login.html",form = form)

# Logout İşlemi
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/bitti/<int:id>")
def bitti(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("Update tasks Set is_completed = ? where id = ? ",(1,id))

    cursor.execute("Update users Set xp = xp + 10 where id = ?",(session["user_id"],))
    
    cursor.execute("SELECT xp, seviye FROM users WHERE id = ?", (session["user_id"],))
    user = cursor.fetchone()
    xp = user["xp"]
    seviye = user["seviye"]
    
    if xp % 100 == 0: 
        seviye = seviye+1
        if seviye == 20:
            level = "D" 
            flash(f'{'Rank E'},{'Rank D'}', 'rankup')
            cursor.execute("UPDATE users SET seviye = ?, xp = ?, level = ? WHERE id = ?", (seviye, xp, level, session["user_id"]))
        elif seviye == 40:
            level = "C"
            flash(f'{'Rank D'},{'Rank C'}', 'rankup')
            cursor.execute("UPDATE users SET seviye = ?, xp = ?, level = ? WHERE id = ?", (seviye, xp, level, session["user_id"]))
        elif seviye == 60:
            level = "B"
            flash(f'{'Rank C'},{'Rank B'}', 'rankup')
            cursor.execute("UPDATE users SET seviye = ?, xp = ?, level = ? WHERE id = ?", (seviye, xp, level, session["user_id"]))
        elif seviye == 80:
            level = "A"
            flash(f'{'Rank B'},{'Rank A'}', 'rankup')
            cursor.execute("UPDATE users SET seviye = ?, xp = ?, level = ? WHERE id = ?", (seviye, xp, level, session["user_id"]))
        elif seviye == 100:
            level = "S"
            flash(f'{'Rank A'},{'Rank S'}', 'rankup')
            cursor.execute("UPDATE users SET seviye = ?, xp = ?, level = ? WHERE id = ?", (seviye, xp, level, session["user_id"]))
        else:
            flash("Leveled up!", "levelup")
            cursor.execute("UPDATE users SET seviye = ?, xp = ? WHERE id = ?", (seviye, xp, session["user_id"]))
             
    else:
        flash("Görevi Tamamladın +10xp","success")
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/bitti_habits/<int:id>")
def bitti_habit(id):
    bugun = date.today()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("Select * from habits where id = ? and user_id = ?",(id,session["user_id"]))
    habit = cursor.fetchall()
    print(habit)
    habit = habit[0]
    frequency = habit["frequency"]
    days = habit["days"].split(",") if habit["days"] else []
    if frequency == "daily":
            tarih = bugun + timedelta(days=1)
            start_date = bugun + timedelta(days=2)
    elif frequency == "weekly":
                tarih = calculate_next_date(frequency, days, bugun)
                start_date = calculate_next_date(frequency, days, tarih)

    cursor.execute("Update habits Set last_completed_date = ?, date = ?, start_date = ?, streak_count = streak_count + 1 where id = ? ",(bugun,tarih,start_date,id))

    cursor.execute("Update users Set xp = xp + 10 where id = ?",(session["user_id"],))
    count = habit["streak_count"] + 1
    if count==21:
        cursor.execute("Update habits Set level = ? where id = ?",("D",id))
    elif count==42:
        cursor.execute("Update habits Set level = ? where id = ?",("C",id))
    elif count==63:
        cursor.execute("Update habits Set level = ? where id = ?",("B",id))
    elif count==90:
        cursor.execute("Update habits Set level = ? where id = ?",("A",id))
    elif count==120:
        cursor.execute("Update habits Set level = ? where id = ?",("S",id))
    
    cursor.execute("SELECT xp, seviye FROM users WHERE id = ?", (session["user_id"],))
    user = cursor.fetchone()
    xp = user["xp"]
    seviye = user["seviye"]
    
    if xp % 100 == 0: 
        seviye = seviye+1
        if seviye == 20:
            level = "D" 
            flash(f'{'Rank E'},{'Rank D'}', 'rankup')
            cursor.execute("UPDATE users SET seviye = ?, xp = ?, level = ? WHERE id = ?", (seviye, xp, level, session["user_id"]))
        elif seviye == 40:
            level = "C"
            flash(f'{'Rank D'},{'Rank C'}', 'rankup')
            cursor.execute("UPDATE users SET seviye = ?, xp = ?, level = ? WHERE id = ?", (seviye, xp, level, session["user_id"]))
        elif seviye == 60:
            level = "B"
            flash(f'{'Rank C'},{'Rank B'}', 'rankup')
            cursor.execute("UPDATE users SET seviye = ?, xp = ?, level = ? WHERE id = ?", (seviye, xp, level, session["user_id"]))
        elif seviye == 80:
            level = "A"
            flash(f'{'Rank B'},{'Rank A'}', 'rankup')
            cursor.execute("UPDATE users SET seviye = ?, xp = ?, level = ? WHERE id = ?", (seviye, xp, level, session["user_id"]))
        elif seviye == 100:
            level = "S"
            flash(f'{'Rank A'},{'Rank S'}', 'rankup')
            cursor.execute("UPDATE users SET seviye = ?, xp = ?, level = ? WHERE id = ?", (seviye, xp, level, session["user_id"]))
        else:
            flash("Leveled up!", "levelup")
            cursor.execute("UPDATE users SET seviye = ?, xp = ? WHERE id = ?", (seviye, xp, session["user_id"]))
             
    else:
        flash("Görevi Tamamladın +10xp","success")
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/aliskanlik")
@login_required
def aliskanlik():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("Select * From habits where user_id = ?",(session["user_id"],))
    habits = cursor.fetchall()
    conn.close()
    return render_template("aliskanlik.html", habits=habits)

@app.route("/takvim")
@login_required
def takvim_today():
    bugun = date.today()
    conn = get_db()
    cursor = conn.cursor()
    bugun = bugun.strftime("%Y-%m-%d")
    cursor.execute("Select * From tasks where user_id = ? and ((date = ?) OR (start_date <= ? AND end_date >= ?) OR end_date IS NULL) and is_completed IS NULL", (session["user_id"], bugun, bugun, bugun))
    gorevler = cursor.fetchall()
    cursor.execute("Select * From daily_notes where user_id = ? and date = ?", (session["user_id"], bugun))
    notlar = cursor.fetchall()
    conn.close()
    today = date.today()
    updated_tasks = []
    for task in gorevler:
            # end_date alanı datetime/datetime64 olabilir, string ise dönüştürmen gerekebilir
            end_date = task["end_date"]
            if isinstance(end_date, datetime):
                end_date = end_date.date()
            days_left = (end_date - today).days if end_date else None

            # dictionary’ye yeni alan ekle
            task["days_left"] = days_left
            updated_tasks.append(task)
    return render_template("takvim.html", tasks=updated_tasks, selected_date=bugun, notlar=notlar)

@app.route("/takvim/<tarih>")
@login_required
def takvim_date(tarih):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("Select * From tasks where user_id = ? and ((date = ?) OR (start_date <= ? AND end_date >= ?) OR end_date IS NULL) and is_completed IS NULL", (session["user_id"], tarih, tarih, tarih))
    gorevler = cursor.fetchall()
    cursor.execute("Select * From daily_notes where user_id = ? and date = ?", (session["user_id"], tarih))
    notlar = cursor.fetchall()
    conn.close() 
    today = date.today()
    updated_tasks = []
    for task in gorevler:
            # end_date alanı datetime/datetime64 olabilir, string ise dönüştürmen gerekebilir
            end_date = task["end_date"]
            if isinstance(end_date, datetime):
                end_date = end_date.date()
            days_left = (end_date - today).days if end_date else None

            # dictionary’ye yeni alan ekle
            task["days_left"] = days_left
            updated_tasks.append(task)
    return render_template("takvim.html", tasks=updated_tasks, selected_date=tarih, notlar=notlar)

@app.route("/profil", methods=["GET","POST"])
@login_required
def profil():
    form = ProfilForm(request.form)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT avatar, mail_notifications FROM users WHERE id=?", (session["user_id"],))
    profil = cursor.fetchone()
    if request.method == "POST" and form.validate():
        if "avatar" in request.form:
            cursor.execute("UPDATE users SET avatar=? WHERE id=?", 
                           (form.avatar.data, session["user_id"]))
        
        # Checkbox kontrolü
        mail_notify_value = form.chekbox.data  # True veya False
        cursor.execute("UPDATE users SET mail_notifications=? WHERE id=?",
                       (mail_notify_value, session["user_id"]))
        
        conn.commit()
        flash("Profil Ayarları Güncellendi", "success")
        return redirect(url_for("profil"))
    
    form.avatar.data = profil["avatar"]
    form.chekbox.data = bool(profil["mail_notifications"])
    cursor.execute("Select * From users where id = ?",(session["user_id"],))
    user = cursor.fetchone()
    yapilan = cursor.execute("Select * From tasks where user_id = ? and is_completed = 1",(session["user_id"],))
    bugun = date.today()
    yapilmayan = cursor.execute("Select * From tasks where user_id = ? and end_date < ? and is_completed IS NULL",(session["user_id"],bugun))

    tekrar = cursor.execute("Select * From tasks where user_id = ? and repeat_type = ? and is_completed = 1",(session["user_id"],'aralikli'))

    aliskan = cursor.execute("Select * From habits where user_id = ?",(session["user_id"],))
    x = cursor.fetchall()
    seri = 0
    for i in x:
        y = i["streak_count"]
        if y > seri:
            seri = y

    xp = user["xp"]

    conn.close()
    return render_template("profil.html", user=user, yapilan = yapilan, yapilmayan = yapilmayan, xp = xp, seri = seri, aliskan= aliskan, tekrar = tekrar, form = form)

@app.route('/api/gunluk-not/<tarih>', methods=['GET'])
def get_gunluk_not(tarih):
    if tarih == "bugun":
        bugun = date.today()   
    else:
        bugun = date
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT note_text, rating FROM daily_notes WHERE user_id = ? AND date = ?", (session["user_id"], bugun))
    gunluk_not = cursor.fetchone()
    conn.close()

    if gunluk_not:
        return jsonify({
            'exists': True,
            'note_text': gunluk_not['note_text'],
            'note_rating': gunluk_not['rating']
        })
    else:
        return jsonify({'exists': False})

@app.route("/not",methods = ["GET","POST"])
@login_required
def notekle():
    if request.method == 'POST':
        gun_notu = request.form.get('gun_notu')

        gun_puani = request.form.get('gun_puani')

        bugun = date.today()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM daily_notes WHERE user_id = ? AND date = ?", (session["user_id"], bugun))
        kayit_sayisi = cursor.fetchone()["count"]

        if kayit_sayisi > 0:
            cursor.execute("UPDATE daily_notes SET note_text = ?, rating = ? WHERE user_id = ? AND date = ?", (gun_notu, gun_puani, session["user_id"], bugun))
            conn.commit()
            conn.close()
            flash("Gün Notunuz Başarıyla Güncellendi","success")
            return redirect(url_for("index"))
        else:
            cursor.execute("INSERT INTO daily_notes (user_id, date, note_text, rating) VALUES(?,?,?,?)", (session["user_id"], bugun, gun_notu, gun_puani))
            conn.commit()
            conn.close()
            flash("Gün Notu ve Puanı Başarıyla Kaydedildi","success")
            return redirect(url_for("index"))

    return redirect(url_for("index"))

@app.route("/ekle/<tarih>",methods = ["GET","POST"])
@login_required
def ekle(tarih):
    form = gorevForm(request.form)

    if request.method == "POST" and form.validate():
        if tarih == "bugun":
            title = form.title.data

            content = form.content.data

            repeat_type = form.repeat_type.data

            bugun = date.today()

            if repeat_type == "daily":
                conn = get_db()
                cursor = conn.cursor()

                cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,bugun,repeat_type,None,bugun))

                conn.commit()

                conn.close()

            elif repeat_type == "weekly":
                end_date = bugun + timedelta(weeks=1)
                conn = get_db()

                cursor = conn.cursor()

                cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,None,repeat_type,bugun,end_date))

                conn.commit()

                conn.close()
            elif repeat_type == "monthly":
                end_date = bugun + timedelta(days=30)
                conn = get_db()

                cursor = conn.cursor()

                cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,None,repeat_type,bugun,end_date))

                conn.commit()

                conn.close()
            elif repeat_type == "suresiz":
                end_date = None
                conn = get_db()

                cursor = conn.cursor()

                cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,None,repeat_type,bugun,end_date))

                conn.commit()

                conn.close()
                
            else:
                aralik = [0,4,11,25,55,115]
                conn = get_db()
                cursor = conn.cursor()
                for index,i in enumerate(aralik, start=1):
                    tarih = bugun + timedelta(days=i)

                    yeni_title = f"{title} {index}. tekrar"

                    cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],yeni_title,content,tarih,repeat_type,None,tarih))

                conn.commit()

                conn.close()
            flash("Görev Başarıyla Eklendi","success")

            return redirect(url_for("index"))
        else:
            title = form.title.data

            content = form.content.data

            repeat_type = form.repeat_type.data

            bugun = tarih

            bugun = datetime.strptime(bugun, "%Y-%m-%d").date()

            if repeat_type == "daily":
                conn = get_db()
                cursor = conn.cursor()

                cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,bugun,repeat_type,None,bugun))

                conn.commit()

                conn.close()

            elif repeat_type == "weekly":
                end_date = bugun + timedelta(weeks=1)
                conn = get_db()

                cursor = conn.cursor()

                cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,None,repeat_type,bugun,end_date))

                conn.commit()

                conn.close()
            elif repeat_type == "monthly":
                end_date = bugun + timedelta(days=30)
                conn = get_db()

                cursor = conn.cursor()

                cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,None,repeat_type,bugun,end_date))

                conn.commit()

                conn.close()
            elif repeat_type == "suresiz":
                end_date = None
                conn = get_db()

                cursor = conn.cursor()

                cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,None,repeat_type,bugun,end_date))

                conn.commit()

                conn.close()
                
            else:
                aralik = [0,4,11,25,55,115]
                conn = get_db()
                cursor = conn.cursor()
                for index,i in enumerate(aralik, start=1):
                    tarih = bugun + timedelta(days=i)

                    yeni_title = f"{title} {index}. tekrar"

                    cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],yeni_title,content,tarih,repeat_type,None,tarih))

                conn.commit()

                conn.close()
            flash("Görev Başarıyla Eklendi","success")

            return redirect(url_for("index"))
    return render_template("ekle.html",form = form)

@app.route("/ekle_takvim/<tarih>",methods = ["GET","POST"])
@login_required
def ekle_tarih(tarih):
    form = gorevForm(request.form)
    today = date.today()
    secilen_tarih = datetime.strptime(tarih, "%Y-%m-%d").date()
    if secilen_tarih < today:
        flash("Bugünden eski bir tarihe görev ekleyemezsiniz !", "danger")
        return redirect(url_for("takvim_date", tarih=tarih))

    if request.method == "POST" and form.validate():
            title = form.title.data

            content = form.content.data

            repeat_type = form.repeat_type.data

            bugun = tarih

            bugun = datetime.strptime(bugun, "%Y-%m-%d").date()

            if repeat_type == "daily":
                conn = get_db()
                cursor = conn.cursor()

                cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,bugun,repeat_type,None,bugun))

                conn.commit()

                conn.close()

            elif repeat_type == "weekly":
                end_date = bugun + timedelta(weeks=1)
                conn = get_db()

                cursor = conn.cursor()

                cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,None,repeat_type,bugun,end_date))

                conn.commit()

                conn.close()
            elif repeat_type == "monthly":
                end_date = bugun + timedelta(days=30)
                conn = get_db()

                cursor = conn.cursor()

                cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,None,repeat_type,bugun,end_date))

                conn.commit()

                conn.close()
            elif repeat_type == "suresiz":
                end_date = None
                conn = get_db()

                cursor = conn.cursor()

                cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,None,repeat_type,bugun,end_date))

                conn.commit()

                conn.close()
                
            else:
                aralik = [0,4,11,25,55,115]
                conn = get_db()
                cursor = conn.cursor()
                for index,i in enumerate(aralik, start=1):
                    tarih = bugun + timedelta(days=i)

                    yeni_title = f"{title} {index}. tekrar"

                    cursor.execute("Insert into tasks(user_id,title,description,date,repeat_type,start_date,end_date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],yeni_title,content,tarih,repeat_type,None,tarih))

                conn.commit()

                conn.close()

            flash("Görev Başarıyla Eklendi","success")

            return redirect(url_for("takvim_date", tarih=tarih))
    return render_template("ekle_takvim.html",form = form)

@app.route("/sil/<int:id>")
@login_required
def delete(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("Select * from tasks where user_id = ? and id = ?",(session["user_id"],id))

    result = cursor.fetchone()

    next_page = request.args.get('next')

    if result :

        cursor.execute("Delete from tasks where id = ?",(id,))

        conn.commit()
        conn.close()
        flash("Görev Silindi","danger")
        if next_page:
          return redirect(next_page)  # geldiği sayfaya dön
    else:
        flash("bu işleme yetkiniz yok","danger")
        if next_page:
          return redirect(next_page)

@app.route("/sil_habits/<int:id>")
@login_required
def delete_habit(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("Select * from habits where user_id = ? and id = ?",(session["user_id"],id))

    result = cursor.fetchone()

    next_page = request.args.get('next')

    if result :

        cursor.execute("Delete from habits where id = ?",(id,))

        conn.commit()
        conn.close()
        flash("Alışkanlık Silindi","danger")
        if next_page:
          return redirect(next_page)  # geldiği sayfaya dön
    else:
        flash("bu işleme yetkiniz yok","danger")
        if next_page:
          return redirect(next_page)

@app.route("/duzenle/<int:id>",methods = ["GET","POST"])
@login_required
def update(id):
   next_page = request.args.get('next')
   if request.method == "GET":
       conn = get_db()
       cursor = conn.cursor()

       result = cursor.execute("Select * from tasks where id = ? and user_id = ?",(id,session["user_id"]))

       if result == 0:
           flash("bu işleme yetkiniz yok","danger")
           return redirect(url_for("index"))
       else:
           tasks = cursor.fetchone()
           form = gorevForm()

           form.title.data = tasks["title"]
           form.content.data = tasks["description"]
           form.repeat_type.data = tasks["repeat_type"]
           return render_template("update.html",form = form)
   else:
       form = gorevForm(request.form)

       newTitle = form.title.data
       newContent = form.content.data
       newrepeat_type = form.repeat_type.data
       conn = get_db()

       cursor = conn.cursor()

       cursor.execute("Update tasks Set title = ?,description = ?,repeat_type = ? where id = ? ",(newTitle,newContent,newrepeat_type,id))

       conn.commit()

       flash("Görev başarıyla güncellendi","success")

       if next_page:
          return redirect(next_page)

@app.route("/duzenle_habits/<int:id>",methods = ["GET","POST"])
@login_required
def update_habit(id):
   next_page = request.args.get('next')
   if request.method == "GET":
       conn = get_db()
       cursor = conn.cursor()

       result = cursor.execute("Select * from habits where id = ? and user_id = ?",(id,session["user_id"]))

       if result == 0:
           flash("bu işleme yetkiniz yok","danger")
           return redirect(url_for("index"))
       else:
           habits = cursor.fetchone()
           form = HabitForm()

           form.title.data = habits["title"]
           form.content.data = habits["description"]
           form.frequency.data = habits["frequency"]
           form.days.data = habits["days"].split(',') if habits["days"] else []
           return render_template("update_habits.html",form = form)
   else:
       form = HabitForm(request.form)

       newTitle = form.title.data
       newContent = form.content.data
       newfrequency = form.frequency.data
       newdays = form.days.data if newfrequency == "weekly" else None
       today = date.today()
       start_date = None    
       tarih = None
       if newfrequency == "daily":
            start_date = today + timedelta(days=1)
            tarih = today
       elif newfrequency == "weekly" and newdays:
            today_name = today.strftime("%a")
            if today_name in newdays:
                tarih = today
                start_date = calculate_next_date(newfrequency, newdays, today)
            else:
                tarih = calculate_next_date(newfrequency, newdays, today)
                start_date = calculate_next_date(newfrequency, newdays, tarih)
       conn = get_db()
       cursor = conn.cursor()
       cursor.execute("Update habits Set title = ?,description = ?,frequency = ?,days = ?,start_date = ?,date = ? where id = ? ",(newTitle,newContent,newfrequency,','.join(newdays) if newdays else None,start_date,tarih,id))
       conn.commit()
       flash("Alışkanlık başarıyla güncellendi","success")

       if next_page:
          return redirect(next_page)
   
@app.route("/aliskanlik_ekle",methods = ["GET","POST"])
@login_required
def ekle_aliskanlik():
    form = HabitForm(request.form)

    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        frequency = form.frequency.data
        days = form.days.data if frequency == "weekly" else None
        today = date.today()
        start_date = None
        tarih = None

        if frequency == "daily":
            start_date = today + timedelta(days=1)
            tarih = today
        elif frequency == "weekly" and days:
            today_name = today.strftime("%a")
            if today_name in days:
                tarih = today
                start_date = calculate_next_date(frequency, days, today)
            else:
                tarih = calculate_next_date(frequency, days, today)
                start_date = calculate_next_date(frequency, days, tarih)
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("Insert into habits(user_id,title,description,frequency,days,start_date,date) VALUES(?,?,?,?,?,?,?)",(session["user_id"],title,content,frequency,','.join(days) if days else None,start_date,tarih))

        conn.commit()

        conn.close()

        flash("Alışkanlık Başarıyla Eklendi","success")

        return redirect(url_for("aliskanlik"))
    else: 
        return render_template("habbits_add.html",form = form)

if __name__ == "__main__":
    app.run(debug=True)