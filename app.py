import os
from flask import Flask,render_template,redirect,flash,request,session,url_for
from flask_mail import Message,Mail
from database import db, users  
import random
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
    
    # FALLBACK: If cache is empty but user is logged in via ay system
    if not user_data:
        email = ay.current_user()
        if email:
            data = users.query.filter_by(email=email).first()
            if data:
                # Rebuild the session cache on the fly!
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

@app.route("/reg" , methods=['POST','GET'])
def handle_reg():
    if request.method=="POST":
        user_name=request.form.get('user_name')
        user_email=request.form.get('user_email')
        password=request.form.get('password')
        cpassword=request.form.get('cpassword')
        session['ee_name'] = user_name
        session['ee_email'] = user_email
        existing_user = users.query.filter_by(email=user_email).first()
        if existing_user:
            flash("Email is already registered", "warning")
            return render_template("reg.html")
        if password != cpassword:
            flash("Password doesnt match","warning")
            return render_template("reg.html")
        
        session['reg_data'] = {
            'name': user_name,
            'email': user_email,
            'age' : None,
            'gender' : None,
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
        return redirect(url_for("reg"))

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
                return redirect(url_for("reg"))
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
            
            # --- CACHE DATA IN SESSION HERE ---
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
    session.pop('user_profile', None)  # Clears out the user profile cache safely
    flash("Logged out", "info")
    return redirect(url_for("home"))

@app.route("/profile")
@ay.protected(fallback_route='handle_login')
def profile():
    user = session.get('user_profile')
    
    # FALLBACK: Re-query and build cache if it vanished out of memory
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
        # 1. Update Database
        data.name = request.form.get('name')
        data.gender = request.form.get('gender')
        data.age = request.form.get('age')
        db.session.commit()
        
        # 2. Synchronize / Refresh the Session Cache!
        session['user_profile'] = {
            'name': data.name,
            'email': data.email,
            'gender': data.gender,
            'age': data.age
        }
        
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))
    
    return render_template("editp.html", name=data.name, gender=data.gender, age=data.age)
 ##-----------------------------------------------Login and logout ends--------------------------------------------------------------------


@app.route("/myspace")
@ay.protected()
def myspace():
    text,aut=quotes()
    return render_template("myspace.html",text=text,aut=aut)


@app.route("/maths")
@ay.protected()
def maths():
    return render_template("smaths.html")

@app.route("/chem")
@ay.protected()
def chem():
    return render_template("schem.html")

@app.route("/phy")
@ay.protected()
def phy():
    return render_template("sphy.html")
    



if __name__ == "__main__":
    app.run(debug=True)