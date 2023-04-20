from whisper import captureAudioReturnResult
from chat import createPrompt, sendChatCompletionWithMessage
from spotify import SpotifyRequest, chatOutputToStructured
import argparse
import sys

# TWILIO_SID = 'SKb501a041f10f49cc28ac99f7063d828e'
TWILIO_SID = 'AC3a1567d7283831d56dabce93bb51dd49'
TWILIO_SECRET = 'mrDHRx4s0l8b5d5R8TvxPW5f7qolV0Yc'
TWILIO_AUTH_TOKEN = '34ef87ad86224742cf0e32f97d24e3b2'
TWILIO_PHONE_NUMBER='+16099084970'

def main():
  spot = SpotifyRequest()
  spot.reinit()
  assert spot.current_user(), 'no current user!!'
  genres = spot.get_genre_seeds()['genres']
  attributes = spot.get_attributes()

  print('say something like: \nmake me a playlist with ambient audio. music that will help me focus. study music but upbeat. Similar to The Chemical Brothers or Justice.')
  # user_request = input('What sort of playlist do you want made? ')
  # print(user_request)
  user_request = 'make me a playlist with ambient audio. music that will help me focus. study music but upbeat. Similar to The Chemical Brothers or Justice'
  prompt = createPrompt(user_request, attrs=attributes, genres=genres)

  output = sendChatCompletionWithMessage(prompt)
  assert output[0] and output[0]['content'], 'chatGPT bad output'
  chat_outputs = output[0]['content']
  print('gpt output: ', chat_outputs)
  s_genres, s_artists, s_attrs = chatOutputToStructured(chat_outputs, attributes=attributes)
  assert s_genres, 'No genres'
  s_artists = spot.artistIdForName(s_artists)
  print('artists: ', s_artists)
  recs = spot.get_recommendations(seed_genres=s_genres, seed_artists=s_artists, attributes=s_attrs)
  assert recs, 'Recs is none'
  track_uris = spot.tracksForRecs(recs)
  playlist_id, playlist_url = spot.get_playlist_info(pname='hackathon')
  spot.playlist_write_tracks(playlist_id, track_uris)

