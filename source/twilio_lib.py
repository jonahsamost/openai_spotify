from flask import Flask, request, redirect
from twilio.twiml.messaging_response import MessagingResponse
from logic import playlist_for_query, ERROR_CODES
from loglib import logger

app = Flask(__name__)
host='0.0.0.0'
host='127.0.0.1'
port=80

FROM='from'
TO='to'

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

def _playlist_for_query(query):
  err, url = playlist_for_query(query)
  logger.info('Error: %s', err)
  logger.info('Url: %s', url)

@app.route("/sms", methods=['GET', 'POST'])
def incoming_sms():
  """Send a dynamic reply to an incoming text message"""
  # Get the message the user sent our Twilio number
  user_request = 'make me a playlist with ambient audio. music that will help me focus. super instrumental. study music but upbeat. high bpm. Similar to The Chemical Brothers or Justice or Fred again..'
  
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
  if body.lower().startswith('create:'):
    query = body[len('create:'):]
    try:
      err, url = _playlist_for_query(query)
    except Exception as e:
      logger.info('Unhandled exception: %s', e)
      err = -1
    if err == ERROR_CODES.NO_ERROR:
      resp.message(f'\n\nCreated! Check the url!!\n\n{url}')
    elif err == ERROR_CODES.ERROR_OPENAI_SEX:
      resp.message(f'seems your query may have been a bit too risque :( .). try again?')
    else:
      resp.message(f'hrm thats an error on our end... try again?')
  else:
    user_request = 'make me a playlist with ambient audio. music that will help me focus. super instrumental. study music but upbeat. high bpm. Similar to The Chemical Brothers or Justice'
    rm = (
      "\n\nWelcome to ThumbTings!!"
      "\n\nif you wanna make a playlist start your message with "
      "\"create:\" then write whatever youre feeling, including genres, artists or song names."
      f"\n\nFor example:\n\"create: {user_request}\""
    )
    resp.message(rm)

  return str(resp)


@app.route("/", methods=['GET'])
def blah():
  return 'LOSING ALL MY INNOCENCE'

if __name__ == "__main__":
    app.run(host=host, port=port)
