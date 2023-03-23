from whisper import captureAudioReturnResult
from chat import createPrompt, sendChatCompletionWithMessage
from spotify import SpotifyRequest, chatOutputToStructured
import argparse
import sys

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--text', action='store_true', default=False)
  args = parser.parse_args()

  spot = SpotifyRequest()
  spot.reinit()
  assert spot.current_user(), 'no current user!!'
  genres = spot.get_genre_seeds()['genres']
  attributes = spot.get_attributes()

  print('say something like: \nmake me a playlist with ambient audio. music that will help me focus. study music but upbeat. Similar to The Chemical Brothers or Justice.')
  if args.text:
    user_request = input('What sort of playlist do you want made? ')
    print(user_request)
  else:
    user_request = captureAudioReturnResult()
  # prompt = createPrompt(user_request)
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
  playlist_id = spot.get_playlist_id(pname='hackathon')
  spot.playlist_write_tracks(playlist_id, track_uris)

main()
