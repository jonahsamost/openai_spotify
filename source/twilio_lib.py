from flask import Flask, request, redirect
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from logic import playlist_for_query, ERROR_CODES
from loglib import logger
import os

app = Flask(__name__)
host='0.0.0.0'
# host='127.0.0.1'
port=8080

FROM='from'
TO='to'

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
THIS_NUMBER = '+16099084970'

convo_list = []
class Conversations():
  def __init__(self, number: str, body: str):
    self.number = number
    self.messages = [{'direction': FROM, 'body': body}]

  def add_message(self, body: str, from_to: str) -> None:
    self.messages.append({'direction': from_to, 'body': body})


def ConversationForNumber(number):
  global convo_list
  for c in convo_list:
    if c.number == number:
      return c
  return None


def _send_twilio_msg(number_id: str, body: str):
  client = Client(account_sid, auth_token)
  message = client.messages.create(
    body=body,
    from_=THIS_NUMBER,
    to=number_id)


def _playlist_for_query(query):
  err, url = playlist_for_query(query)
  logger.info('Error: %s', err)
  logger.info('Url: %s', url)
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
  global convo_list
  convo = ConversationForNumber(number_id)
  if convo:
    convo.add_message(body=body, from_to=FROM)
  else:
    convo_list.append(Conversations(number_id, body))

  # Start our TwiML response
  resp = MessagingResponse()

  # Determine the right reply for this message
  logger.info(f'received message: {body} from {number_id}')

  make_me = (
    "\n\nIf you want to make a playlist start your message with: "
    "make me a playlist... then write whatever youre feeling, including genres, artists or song names."
    f"\n\nFor example:\n\"{prologue} {user_request}\""
    )
  if body.lower().startswith(prologue.lower()):
    query = body[len(prologue):]

    # handle case where the user doesnt input anything
    if not query.strip():
      rm = "I didn't understand that..." + make_me
      resp.message(rm)
      return str(resp)
    try:
      _send_twilio_msg(number_id, "Thanks for your message! We're working on it...")
      query = body
      err, url = _playlist_for_query(query)
    except Exception as e:
      logger.info('Unhandled exception: %s', e)
      err = -1
    if err == ERROR_CODES.NO_ERROR:
      out_msg = (
        '\n\nCreated! Check the url!!\n'
        'This playlist will self-destruct in 3 days, so signup to get unlimited, time-limitless playlists\n'
        f'{url}'
      )
      _send_twilio_msg(number_id, out_msg)
      return ''
    elif err == ERROR_CODES.ERROR_NO_GEN:
      out_msg = 'seems your query may have been a bit too risque :( .). try again?'
      _send_twilio_msg(number_id, out_msg)
    else:
      out_msg = 'hrm thats an error on our end... try again?'
      _send_twilio_msg(number_id, out_msg)
  else:
    user_request = 'make me a playlist with ambient audio. music that will help me focus. super instrumental. study music but upbeat. high bpm. Similar to The Chemical Brothers or Justice'
    rm = "\n\nWelcome to ThumbTings!!" + make_me
    _send_twilio_msg(number_id, rm)

  return ''


@app.route("/", methods=['GET'])
def blah():
  return 'LOSING ALL MY INNOCENCE'

if __name__ == "__main__":
    app.run(host=host, port=port)

