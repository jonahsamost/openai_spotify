from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask import make_response, redirect, abort, jsonify
from flask_cors import cross_origin
from flask_login import login_user, logout_user, login_required, LoginManager, current_user
from werkzeug.security import generate_password_hash, check_password_hash

import os
import json
import secrets
import requests
import string
from urllib.parse import urlencode

auth = Blueprint('auth', __name__)
from loglib import logger
import twilio_lib
from twilio_lib import app
import ttdb
import spotify
import logic
from logic import ERROR_CODES

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

@app.route('/spotify', methods=["GET"])
def spotify_landing():
  return redirect(url_for('landing'))


@app.route('/spotify', methods=["POST"])
def spotify_login():
  query = request.form.get('query')
  placeholder = request.form.get('ta_placeholder')
  query = query or placeholder

  # if not current_user.is_authenticated:
  #   flash('Login!')
  #   session['spotify_query'] = query
  #   return redirect(url_for('login'))

  logger.info('user placeholder: |%s|', placeholder)
  logger.info('user query: %s', query)


  nquery = 'Make me a musical playlist that conforms to: ' + query
  err_code, playlist_info = logic.playlist_for_query(
                                          nquery,
                                          number_id=str(current_user.get_id()),
                                          include_all_playlist_info=True)

  if err_code == ERROR_CODES.NO_ERROR:
    # flash("Success!")
    playlist_url, playlist_cover = playlist_info
    return render_template('index.html', playlist_url=playlist_url, playlist_cover=playlist_cover)
  else:
    flash("Sorry, we couldn't understand your last message, try again!")
    return redirect(url_for('landing'))

  _ = ''' 
  if session.get('tokens', None) and session['tokens'].get('access_token', None):
    nquery = 'Make me a musical playlist that conforms to: ' + query
    err_code = ERROR_CODES.NO_ERROR
    err_code, playlist_info = logic.playlist_for_query(
      nquery,
      number_id=str(current_user.get_id()),
      access_token=session['tokens'].get('access_token'),
      refresh_token=session['tokens'].get('refresh_token'),
    )
    if err_code != ERROR_CODES.ERROR_SPOTIFY_REFRESH:
      if err_code == ERROR_CODES.NO_ERROR:
        # flash("Success!")
        playlist_url, playlist_cover = playlist_info
        return render_template('index.html', playlist_url=playlist_url, playlist_cover=playlist_cover)
        # return redirect(url_for('landing', playlist_url=playlist_url))
      else:
        flash("Sorry, we couldn't understand your last message, try again!")
        # return render_template('index.html')
        return redirect(url_for('landing'))

  return spotify_make_response(query)
  '''


def spotify_make_response(query):
  state = ''.join(
      secrets.choice(string.ascii_uppercase + string.digits) for _ in range(16)
      )
  payload = {
    'client_id': spotify.s_id,
    'response_type': 'code',
    'redirect_uri': spotify.s_redirect,
    'state': state,
    'scope': ' '.join(spotify.scope),
    }

  res = make_response(redirect(f'{spotify.AUTH_URL}/?{urlencode(payload)}'))
  res.set_cookie('spotify_auth_state', state)
  session['spotify_query'] = query
  return res


@app.route('/spotify_callback')
def spotify_callback():
  error = request.args.get('error')
  code = request.args.get('code')
  state = request.args.get('state')
  stored_state = request.cookies.get('spotify_auth_state')

  if state is None or state != stored_state:
    logger.info('Error message: %s', repr(error))
    logger.info('State mismatch: %s != %s', stored_state, state)
    spotify_make_response(session['spotify_query'])

 # Request tokens with code we obtained
  payload = {
    'grant_type': 'authorization_code',
    'code': code,
    'redirect_uri': spotify.s_redirect,
  }
  res = requests.post(
    spotify.TOKEN_URL,
    auth=(spotify.s_id, spotify.s_secret),
    data=payload)
  res_data = res.json()

  if res_data.get('error') or res.status_code != 200:
    logger.info(
      'Failed to receive token: %s',
      res_data.get('error', 'No error information received.'),
    )
    abort(res.status_code)

  session['tokens'] = {
    'access_token': res_data.get('access_token'),
    'refresh_token': res_data.get('refresh_token'),
  }

  logger.info('spotify callback The users query is: %s', session['spotify_query'])

  # err_code, playlist_url = logic.playlist_for_query(
  #   session['spotify_query'],
  #   number_id=str(current_user.get_id()),
  #   token=session['tokens'].get('access_token') 
  # )
  return redirect(url_for('landing', query=session['spotify_query'], ready=True))


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
  
  return redirect(url_for('landing', query=session['spotify_query']))


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
  return redirect(url_for('landing', query=session['spotify_query']))


@app.route('/logout')
@login_required
def logout():
  try:
    logout_user()
    flash("Logged out!")
  except Exception as e:
    logger.info("Logout exception: %s", e)
  return redirect(url_for('landing'))

