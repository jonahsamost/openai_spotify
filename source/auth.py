from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
from loglib import logger

auth = Blueprint('auth', __name__)
import twilio_lib
from twilio_lib import app
import ttdb

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
  db = twilio_lib.db  
  user = db.load_subscriber(user_id)
  if not user:
    return None
  return ttdb.UserPass(*user[0])


@app.route('/login')
def login():
  return render_template('login.html', body_class="text-center", include_js=False)


@app.route('/login', methods=['POST'])
def login_post():
  email = request.form['email']
  password = request.form['password']
  remember = True if request.form.get('remember-me') else False

  db = twilio_lib.db  
  user = db.get_subscriber(email)
  if not user:
    flash('Please check your login credentials and try again.')
    return redirect(url_for('login'))

  user = ttdb.UserPass(*user[0])
  if not check_password_hash(user.password, password):
    flash('Please check your login credentials and try again.')
    return redirect(url_for('login'))

  login_user(user, remember=remember)
  
  return redirect(url_for('landing'))


@app.route('/signup')
def signup():
  return render_template('signup.html')


@app.route('/signup', methods=['POST'])
def signup_post():
  name = request.form['name']
  email = request.form['email']
  password = request.form['password']
  conf_password = request.form['password_confirm']

  if password != conf_password:
    flash('Passwords do not match!') 
    return redirect(url_for('signup'))

  if len(name) > 99:
    flash('Name too long!')
    return redirect(url_for('signup'))

  db = twilio_lib.db  
  if db.get_subscriber(email):
    flash('Email address already exists!')
    return redirect(url_for('signup'))

  new_user = ttdb.UserPass(
    user_id=None,
    email=email,
    password=generate_password_hash(password, method='sha256'),
    name=name)
  db.add_subscriber(new_user)

  new_user = db.get_subscriber(email)
  new_user = ttdb.UserPass(*new_user[0])

  # grant user session here
  login_user(new_user, remember=True)

  flash('Sign up successful!')
  return redirect(url_for('landing'))


@app.route('/logout')
@login_required
def logout():
  try:
    logout_user()
    flash('You have been logged out.')
  except Exception as e:
    logger.info("Logout exception: %s", e)
  return redirect(url_for('landing'))

