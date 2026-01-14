from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
import os

app = Flask(__name__)
# Secret key
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

# Database (Railway injects DATABASE_URL)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///app.db")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db = SQLAlchemy(app)
migrate = Migrate(app, db)

# =========================
# Models
# =========================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)

    role = db.Column(db.String(50))
    address = db.Column(db.String(100))
    linkdin = db.Column(db.String(100))
    about = db.Column(db.String(300))

    title = db.Column(db.String(300))
    company = db.Column(db.String(300))
    desc = db.Column(db.String(300))

    resume = db.Column(db.String(150))
    image = db.Column(db.String(150), default="static/uploads/profile_pics/default.jpg")

    apply = db.Column(db.Integer, default=0)
    shortlist = db.Column(db.Integer, default=0)
    interview = db.Column(db.Integer, default=0)
    reject = db.Column(db.Integer, default=0)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(150))
    company = db.Column(db.String(100))
    job_url = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

# =========================
# Helpers
# =========================

def fetch_remotive_jobs(role):
    data = requests.get("https://remotive.com/api/remote-jobs").json()["jobs"]
    words = role.lower().split() if role else []
    return [job for job in data if any(w in job["title"].lower() for w in words)][:30]

# =========================
# Routes
# =========================

@app.route("/")
def home():
    return render_template("main.html")

from sqlalchemy.exc import IntegrityError

@app.route("/signup", methods=["POST"])
def signup():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return render_template(
            "signup.html",
            error="Email already registered. Please log in."
        )

    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password)
    )

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return render_template(
            "signup.html",
            error="Email already exists."
        )

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            return redirect(url_for("dashboard", id=user.id))
    return render_template("login.html")

@app.route("/dashboard/<int:id>")
def dashboard(id):
    user = User.query.get_or_404(id)
    jobs = fetch_remotive_jobs(user.role)
    return render_template("dashboard.html", user=user, jobs=jobs)

@app.route("/jobs/<int:id>")
def jobs(id):
    user = User.query.get_or_404(id)
    jobs = fetch_remotive_jobs(user.role)
    return render_template("job_listings.html", user=user, jobs=jobs)

@app.route("/profile/<int:id>")
def profile(id):
    user = User.query.get_or_404(id)
    return render_template("profile.html", user=user)

@app.route("/editprofile/<int:id>", methods=["GET", "POST"])
def editprofile(id):
    user = User.query.get_or_404(id)

    if request.method == "POST":
        user.name = request.form.get("name")
        user.role = request.form.get("role")
        user.address = request.form.get("address")
        user.linkdin = request.form.get("linkedin")  
        user.about = request.form.get("about")

        user.title = "||".join(request.form.getlist("title[]"))
        user.company = "||".join(request.form.getlist("company[]"))
        user.desc = "||".join(request.form.getlist("desc[]"))

        photo = request.files.get("photo")
        if photo and photo.filename:
            path = f"static/uploads/profile_pics/{secure_filename(photo.filename)}"
            photo.save(path)
            user.image = path

        resume = request.files.get("resume")
        if resume and resume.filename:
            path = f"static/uploads/resume/{secure_filename(resume.filename)}"
            resume.save(path)
            user.resume = path

        db.session.commit()
        return redirect(url_for("profile", id=id))

    return render_template("edit_profile.html", user=user)

@app.route("/auto_apply/<int:id>")
def auto_apply(id):
    user = User.query.get_or_404(id)

    app_entry = Application(
        job_title=request.args.get("title"),
        company=request.args.get("company"),
        job_url=request.args.get("job"),
        user_id=user.id
    )

    db.session.add(app_entry)
    user.apply += 1
    db.session.commit()

    return redirect(url_for("applications", id=id))

@app.route("/applications/<int:id>")
def applications(id):
    user = User.query.get_or_404(id)
    apps = Application.query.filter_by(user_id=id).all()

    applied = user.apply or 1
    funnel = {
        "applied": 100,
        "shortlisted": int(user.shortlist * 100 / applied),
        "interview": int(user.interview * 100 / applied)
    }

    return render_template(
        "applications.html",
        user=user,
        apps=apps,
        funnel=funnel
    )

# =========================
# Run
# =========================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
