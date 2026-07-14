import os
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class users(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column("name", db.String(45), nullable=True)
    email = db.Column("email", db.String(120), nullable=False, unique=True)
    password = db.Column("password", db.String(500), nullable=False)
    age = db.Column("age", db.Integer, nullable=True)
    gender = db.Column("gender", db.String(100), nullable=True)
    about = db.Column("about", db.Text, nullable=True)
    phonen = db.Column("phonen", db.String(20), nullable=True)