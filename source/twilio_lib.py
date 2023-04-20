from flask import Flask, request, redirect
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)
host='0.0.0.0'
port=80

FROM='from'
TO='to'

class Conversations():
  def __init__(self, name: str, body: str):
    self.name = name
    self.messages = [{'direction': FROM, 'body': body}]

  def add_message(self, body: str, from_to: str) -> None:
    self.messages.append([{direction: from_to, 'body': body}])

convo_list = []

@app.route("/sms", methods=['GET', 'POST'])
def incoming_sms():
  """Send a dynamic reply to an incoming text message"""
  # Get the message the user sent our Twilio number
  body = request.values.get('Body', None)
  number_id = request.values.get('from', None)

  # Start our TwiML response
  resp = MessagingResponse()

  # Determine the right reply for this message
  if body.startswith('create:')
    resp.message("Hi!")
  else:
    user_request = 'make me a playlist with ambient audio. music that will help me focus. super instrumental. study music but upbeat. high bpm. Similar to The Chemical Brothers or Justice'
    rm = (
      "I didn't understand your message, if you wanna make a playlist start your message with "
      "\"create:\" then write whatever youre feeling, including genres, artists or song names. "
      f"For example, \"create: {user_request}\""
    )
    resp.message("\"create:\" then")

  return str(resp)

if __name__ == "__main__":
    app.run(debug=True, host=host, port=port)
