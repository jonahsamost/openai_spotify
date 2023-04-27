from flask import Flask, request, redirect
from flask import send_from_directory, render_template
from flask_basicauth import BasicAuth
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from logic import playlist_for_query, ERROR_CODES
from loglib import logger
import ttdb
import os
import spotify
from datetime import datetime as dt
from datetime import timedelta
import re

app = Flask(__name__)

app.config['BASIC_AUTH_REALM'] = 'realm'
app.config['BASIC_AUTH_USERNAME'] = os.environ['BASIC_AUTH_USER']
app.config['BASIC_AUTH_PASSWORD'] = os.environ['BASIC_AUTH_PASS']
basic_auth = BasicAuth(app)

host='0.0.0.0'
port=8080

FROM='from'
TO='to'

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
THIS_NUMBER = '+16099084970'
VCF_HOSTING_PATH = 'https://tt.thumbtings.com:4443/reports/ThumbTings.vcf'

db = ttdb.TTDB()

@app.route('/testing')
def render():
  return render_template('index.html')


@app.route('/login')
def login():
  return render_template('login.html', body_class="text-center", include_js=False)


@app.route('/cron/background', methods=['GET'])
@basic_auth.required
def background_jobs():
  # started from a cronjob because hack shit

  logger.info('delete old playlists')
  q = f'select * from {db.playlist_table} where public = 1 and time_created < %s and deleted = 0'
  results = db.execute(q, (dt.now() - timedelta(hours=72)))
  for result in results:
    playlist = ttdb.Playlist(*result)
    pid = playlist.playlist_id
    spot = spotify.SpotifyRequest()
    spot.reinit()
    spot.playlist_delete_tracks(pid)
    spot.playlist_make_private(pid)
    q = f'update {db.playlist_table} set deleted=1 where playlist_id = %s'
    db.execute(q, (pid))

  logger.info('send contact info')
  q = f'select * from {db.user_table} where playlist_created=1 and contact_sent=0'
  results = db.execute(q)
  for result in results:
    user = ttdb.Users(*result)
    logger.info('Sending contact to %s', user.phone_number)
    _send_vcf_msg(user.phone_number)
    q = f'update {db.user_table} set contact_sent=1 where phone_number = %s'
    db.execute(q, (user.phone_number))

  return ''

def _send_twilio_msg(number_id: str, body: str):
  client = Client(account_sid, auth_token)
  message = client.messages.create(
    body=body,
    from_=THIS_NUMBER,
    to=number_id)


@app.route('/reports/<path:name>')
def send_vcf(name):
  if name == 'ThumbTings.vcf':
    return send_from_directory('reports', 'ThumbTings.vcf')
  else:
    return ''

VCF_MSG = "We hope you're enjoying the playlist! Add ThumbTings to your contacts to never miss a beat!"
def _send_vcf_msg(number_id: str):
  client = Client(account_sid, auth_token)
  message = client.messages.create(
    body=VCF_MSG,
    from_=THIS_NUMBER,
    media_url=[VCF_HOSTING_PATH],
    to=number_id)


def _playlist_for_query(query, number_id):
  err, url = playlist_for_query(query, number_id)
  logger.info('%s: Error: %s', number_id, err)
  logger.info('%s: Url: %s', number_id, url)
  return err, url


@app.route("/sms", methods=['GET', 'POST'])
def incoming_sms():
  """Send a dynamic reply to an incoming text message"""
  # Get the message the user sent our Twilio number
  user_request = 'with ambient audio. music that will help me focus. super instrumental. study music but upbeat. high bpm. Similar to The Chemical Brothers or Justice or Fred again..'
  prologue = 'Make me a playlist' 
  prologue_len = len(prologue)
    
  body = request.values.get('Body', None)
  number_id = request.values.get('From', None)
  if not body or not number_id:
    return ''

  # Determine the right reply for this message
  ab = [ord(c) for c in body]
  logger.info('%s: received message: |%s|ab|', number_id, body, ab)
  
  # add user to user db if we havent seen before
  if not db.get_user(number_id):
    logger.info('%s: Got new user!', number_id)
    # TODO for testing in beta only!!!!! remove when ready
    subd = 1 if db.get_user_count() < 100 else 0
    if not subd:
      out_msg = 'Not accepting any more users at this time...check back in a bit'
      _send_twilio_msg(number_id, out_msg)
      return ''

    newuser = ttdb.Users(phone_number=number_id,
      subscribed=subd, playlist_created=0, contact_sent=0)
    db.user_insert(newuser.dict())

  # add user message to message table
  user_msg = ttdb.UserMessages(phone_number=number_id, message=body)
  db.user_message_insert(user_msg.dict())

  make_me = (
    "\n\nIf you want to make a playlist start your message with: "
    "make me a playlist... then write whatever you're feeling, including genres, artists or song names."
    f"\n\nFor example:\n\"{prologue} {user_request}\""
    )
  if re.match('make me a play(\ )?list', body.lower()):

    cur_user = db.get_user(number_id)
    if not cur_user:
      logger.info('%s: Cur user is none', number_id)
      # should never hit this case as user was just created
      out_msg = 'hrm thats an error on our end... '
      _send_twilio_msg(number_id, out_msg)
      return ''
    
    cur_user = ttdb.Users(*cur_user[0])
    if not cur_user.subscribed and cur_user.playlist_created:
      out_msg = (
        "You've already created a playlist! "
        "Sign up to get unlimited, time-limitless playlists")
      _send_twilio_msg(number_id, out_msg)
      return ''


    url = ''
    unhandled_err = ''
    # handle case where the user doesnt input anything
    if not body[len(prologue):].strip():
      out_msg = "I didn't understand that..." + make_me
      _send_twilio_msg(number_id, out_msg)

    try:
      _send_twilio_msg(number_id, "Thanks for your message! We're working on it...")
      err, url = _playlist_for_query(body, number_id)
    except Exception as e:
      logger.info('%s: Unhandled exception: %s', number_id, e)
      unhandled_err = e
      err = -1
    if err == ERROR_CODES.NO_ERROR:
      out_msg = (
        '\n\nCreated! Check the url!!\n'
        'This playlist will self-destruct in 3 days, so signup to get unlimited, time-limitless playlists\n'
        f'{url}'
      )
      _send_twilio_msg(number_id, out_msg)
    else:
      out_msg = "We couldn't create a playlist for your input... Try again?"
      _send_twilio_msg(number_id, out_msg)
      return ''

    url_id = url.split('/')[-1] if err == ERROR_CODES.NO_ERROR else ''
    plist = ttdb.Playlist(
      phone_number=number_id, playlist_id=url_id, prompt=body,
      success=int(err == ERROR_CODES.NO_ERROR),
      time_created=dt.now(), 
      public=1, # TODO change when subscription is ready
      error_message=unhandled_err,
      deleted=0)
    db.playlist_insert(plist.dict())
    if not cur_user.playlist_created:
      db.user_created_playlist(number_id)
  # gets hit if a user likes/loves/blah the message
  elif re.match("[A-Z][a-z]* [^\x00-\x7f]+.*[^\x00-\x7f]+", out):
    pass
  elif body.find('Hello ThumbTings!') == 0:
    user_request = 'make me a playlist with ambient audio. music that will help me focus. super instrumental. study music but upbeat. high bpm. Similar to The Chemical Brothers or Justice'
    rm = "\n\nWelcome to ThumbTings!!" + make_me
    _send_twilio_msg(number_id, rm)
  else:
    msg = "Hey, we didn't understand that last message! Try again!"
    _send_twilio_msg(number_id, msg)

  return ''


@app.route("/", methods=['GET'])
def blah():
  return 'LOSING ALL MY INNOCENCE'

if __name__ == "__main__":
    app.run(host=host, port=port)

