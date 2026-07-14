import os
import random
from flask import Flask, render_template, redirect, flash, request, session, url_for
from flask_mail import Message, Mail
from database import db, users, UserProgress
from syllabus import JEE_SYLLABUS
import ay_loginsys as ay
from dotenv import load_dotenv
from backend import quotes

app = Flask(__name__, instance_path='/tmp/instance')
load_dotenv()


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'desiralabs@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = 'desiralabs@gmail.com'

mail = Mail(app) 
app.secret_key = "gvshdf"

database_url = os.environ.get("DATABASE_URL")
if os.environ.get("FLASK_ENV") == "development" or not database_url:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'local.db')}"
else:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    ay.set_session_time(days=30)

@app.context_processor
def inject_auth():
    user_data = session.get('user_profile') 
    if not user_data:
        email = ay.current_user()
        if email:
            data = users.query.filter_by(email=email).first()
            if data:
                user_data = {
                    'name': data.name,
                    'email': data.email,
                    'gender': data.gender,
                    'age': data.age
                }
                session['user_profile'] = user_data
    return dict(current_user=user_data)



@app.route("/", methods=['POST','GET'])
def home():
    return render_template("home.html")

@app.route("/test")
def test():
    data = users(email="idk@gmail.com", name="idk", password="hehe")
    db.session.add(data)
    db.session.commit()
    return "done"



@app.route("/reg", methods=['POST','GET'])
def handle_reg():
    if request.method == "POST":
        user_name = request.form.get('user_name')
        user_email = request.form.get('user_email')
        password = request.form.get('password')
        cpassword = request.form.get('cpassword')
        session['ee_name'] = user_name
        session['ee_email'] = user_email
        
        existing_user = users.query.filter_by(email=user_email).first()
        if existing_user:
            flash("Email is already registered", "warning")
            return render_template("reg.html")
        if password != cpassword:
            flash("Password doesnt match", "warning")
            return render_template("reg.html")
        
        session['reg_data'] = {
            'name': user_name,
            'email': user_email,
            'age': None,
            'gender': None,
            'password': ay.hash_it(password) 
        }
        
        otp = str(random.randint(100000, 999999))
        session['reg_otp'] = otp

        try:
            msg = Message(
                subject="Verify Your Email - OTP Verification",
                recipients=[user_email],
                body=f"Hello {user_name},\n\nYour OTP for registration is: {otp}\n\nThis OTP is valid for this session."
            )
            mail.send(msg)
            flash("An OTP has been sent to your email address.", "info")
            return redirect(url_for("verify_otp")) 
            
        except Exception as e:
            session.pop('reg_data', None)
            session.pop('reg_otp', None)
            flash("Failed to send OTP email. Please try again.", "danger")
            return render_template("reg.html")

    return render_template("reg.html")

@app.route("/verify_otp", methods=['POST','GET'])
def verify_otp():
    if 'reg_data' not in session or 'reg_otp' not in session:
        flash("Session expired. Please register again.", "warning")
        return redirect(url_for("handle_reg"))

    if request.method == "POST":
        user_otp = request.form.get("otp")
        if user_otp == session['reg_otp']:
            reg_data = session['reg_data']
            try:
                new_user = users(
                    name=reg_data['name'], 
                    email=reg_data['email'], 
                    password=reg_data['password']
                )
                db.session.add(new_user)
                db.session.commit()
                
                email = reg_data['email']
                session.pop('reg_data', None)
                session.pop('reg_otp', None)

                ay.login(user_id=email, remember=True)
                session['user_profile'] = {
                    'name': new_user.name,
                    'email': new_user.email,
                    'gender': new_user.gender,
                    'age': new_user.age
                }
                flash("Email verified successfully! Welcome.", "success")
                return redirect(url_for("home"))

            except Exception:
                db.session.rollback()
                flash("An unexpected error occurred. Please try again.", "danger")
                return redirect(url_for("handle_reg"))
        else:
            flash("Invalid OTP code. Please check your email and try again.", "danger")

    return render_template("verify_otp.html")

@app.route("/login", methods=['POST', 'GET'])
def handle_login():
    if request.method == "POST":
        user_email = request.form.get('email')
        password = request.form.get('password')
        data = users.query.filter_by(email=user_email).first()
        
        if data and ay.check_it(data.password, password):
            ay.login(user_id=user_email, remember=True)
            
            session['user_profile'] = {
                'name': data.name,
                'email': data.email,
                'gender': data.gender,
                'age': data.age
            }
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password", "danger")
            return render_template("login.html")
            
    return render_template("login.html")

@app.route("/logout")
def handle_logout():
    ay.logout()
    session.pop('user_profile', None)  
    flash("Logged out", "info")
    return redirect(url_for("home"))

# --- User Spaces & Profiles ---

@app.route("/profile")
@ay.protected(fallback_route='handle_login')
def profile():
    user = session.get('user_profile')
    if not user:
        email = ay.current_user()
        data = users.query.filter_by(email=email).first()
        if data:
            user = {
                'name': data.name,
                'email': data.email,
                'gender': data.gender,
                'age': data.age
            }
            session['user_profile'] = user
            
    if user:
        return render_template(
            "profile.html", 
            name=user['name'], 
            email=user['email'], 
            gender=user['gender'], 
            age=user['age']
        )
    return redirect(url_for("handle_login"))

@app.route("/editp", methods=['POST', 'GET'])
@ay.protected(fallback_route='handle_login')
def editp():
    email = ay.current_user()
    data = users.query.filter_by(email=email).first()
    if not data:
        return "User not found", 404

    if request.method == "POST":
        data.name = request.form.get('name')
        data.gender = request.form.get('gender')
        data.age = request.form.get('age')
        db.session.commit()
        
        session['user_profile'] = {
            'name': data.name,
            'email': data.email,
            'gender': data.gender,
            'age': data.age
        }
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))
    
    return render_template("editp.html", name=data.name, gender=data.gender, age=data.age)

""" @app.route("/myspace")
@ay.protected(fallback_route='handle_login')
def myspace():
    text, aut = quotes()
    return render_template("myspace.html", text=text, aut=aut)

@app.route("/maths")
@ay.protected(fallback_route='handle_login')
def maths():
    return render_template("smaths.html")

@app.route("/chem")
@ay.protected(fallback_route='handle_login')
def chem():
    return render_template("schem.html")

@app.route("/phy")
@ay.protected(fallback_route='handle_login')
def phy():
    return render_template("sphy.html") """

@app.route('/myspace')
@ay.protected(fallback_route='handle_login') 
def myspace():
    
    email = ay.current_user()
    
    
    user_record = users.query.filter_by(email=email).first()
    if not user_record:
        return redirect(url_for('handle_login'))
    
   
    user_records = user_record.progress_records 
    
    
    stats = {
        "Physics": {"solved": 0, "total_topics": 15, "done": 0},      
        "Chemistry": {"solved": 0, "total_topics": 17, "done": 0},
        "Mathematics": {"solved": 0, "total_topics": 16, "done": 0}
    }
    
    
    for rec in user_records:
        if rec.topic_id.startswith("phy_"):
            stats["Physics"]["solved"] += rec.questions_solved
            if rec.is_completed: stats["Physics"]["done"] += 1
        elif rec.topic_id.startswith("chm_"):
            stats["Chemistry"]["solved"] += rec.questions_solved
            if rec.is_completed: stats["Chemistry"]["done"] += 1
        elif rec.topic_id.startswith("mat_"):
            stats["Mathematics"]["solved"] += rec.questions_solved
            if rec.is_completed: stats["Mathematics"]["done"] += 1

    
    for sub in stats:
        total = stats[sub]["total_topics"]
        done = stats[sub]["done"]
        stats[sub]["pct"] = int((done / total) * 100) if total > 0 else 0
        stats[sub]["remaining"] = total - done

    
    text, aut = quotes()

    return render_template('myspace.html', stats=stats, text=text, aut=aut)
    


@app.route('/tracker')
@ay.protected(fallback_route='handle_login')
def tracker_dashboard():
    
    email = ay.current_user()
    user_record = users.query.filter_by(email=email).first()
    if not user_record:
        return redirect(url_for('handle_login'))
        
    user_records = UserProgress.query.filter_by(user_id=user_record._id).all()
    
    progress_map = {
        rec.topic_id: {
            "completed": rec.is_completed,
            "questions": rec.questions_solved,
            "notes": rec.notes or ""
        }
        for rec in user_records
    }
    
    return render_template('tracker.html', syllabus=JEE_SYLLABUS, progress=progress_map)

@app.route('/update-progress', methods=['POST'])
@ay.protected(fallback_route='handle_login')
def update_progress():
    
    email = ay.current_user()
    user_record = users.query.filter_by(email=email).first()
    if not user_record:
        return "Unauthorized", 401

    topic_id = request.form.get('topic_id')
    if not topic_id:
        flash("Invalid request data.", "danger")
        return redirect('/tracker')

    

    is_completed_list = request.form.getlist('is_completed')
    is_completed = 'true' in is_completed_list

    questions_solved = int(request.form.get('questions_solved', 0) or 0)
    notes = request.form.get('notes', '').strip()

    
    progress = UserProgress.query.filter_by(user_id=user_record._id, topic_id=topic_id).first()
    
    if not progress:
        progress = UserProgress(user_id=user_record._id, topic_id=topic_id)
        db.session.add(progress)

    
    progress.is_completed = is_completed
    progress.questions_solved = questions_solved
    progress.notes = notes

    try:
        db.session.commit()
        flash("Progress synced successfully!", "success")
    except Exception:
        db.session.rollback()
        flash("Could not update tracking metrics.", "danger")

    return redirect('/tracker')

if __name__ == "__main__":
    app.run(debug=True)