from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.user import User

auth_bp = Blueprint("auth", __name__)


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Debe iniciar sesión para ingresar al sistema.", "warning")
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)
    return wrapped_view


# 🔥 LOGIN ADMIN (solo acceso interno)
@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username, is_active=True).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["full_name"] = user.full_name
            session["role"] = user.role

            flash("Ingreso correcto al sistema.", "success")
            return redirect(url_for("dashboard"))

        flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")


# 🔥 LOGOUT
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("home"))
