from enum import Enum
from loglib import logger
import argparse
import chat
import cohere_lib
import os
import spotify
import sys

class ERROR_CODES(Enum):
  NO_ERROR=0
  ERROR_NO_SPOTIFY_USER=1
  ERROR_CHAT_GPT=2
  ERROR_NO_SPOTIFY_RECS=3
  ERROR_NO_PLAYLIST_CREATE=4
  ERROR_NO_GEN=5
  ERROR_COHERE_GEN=6

def playlist_for_query(user_query: str):
  """Responds with tuple of (Error, Message)."""
  spot = spotify.SpotifyRequest()
  spot.reinit()
  if not spot.current_user():
    return ERROR_CODES.ERROR_NO_SPOTIFY_USER, None

  genres = spot.get_genre_seeds()['genres']
  attributes = spot.get_attributes()
  msgs = chat.create_prompt(user_query, attrs=attributes, genres=genres)

  chat_outputs = chat.get_assistant_message(msgs)
  if not chat_outputs:
    return ERROR_CODES.ERROR_CHAT_GPT, None
  logger.info('openai output: %s', chat_outputs)
  using_cohere = False
  s_genres, s_artists, s_songs, s_attrs = spotify.chatOutputToStructured(chat_outputs, attributes=attributes)

  # could openai successfully generate?
  # try with cohere if not
  if not any([s_genres, s_artists, s_songs, s_attrs]):
    chat_outputs = cohere_lib.get_assistant_message(msgs)
    logger.info('cohere output: %s', chat_outputs)
    if not chat_outputs:
      return ERROR_CODES.ERROR_COHERE_GEN, None
    s_genres, s_artists, s_songs, s_attrs = spotify.chatOutputToStructured(chat_outputs, attributes=attributes)
    if not any([s_genres, s_artists, s_songs, s_attrs]):
      return ERROR_CODES.ERROR_NO_GEN, None
    using_cohere = True

  s_artists = s_artists + list(s_songs.values())
  logger.info('before genres: %s', s_genres)
  s_genres = [g for g in s_genres if g in genres]
  logger.info('after genres: %s', s_genres)
  logger.info('artists: %s', s_artists)
  logger.info('songs: %s', s_songs)
  logger.info('attributes: %s', s_attrs)
  s_artists = spot.IdsForArtists(s_artists)
  s_songs = spot.IdsForSongs(s_songs)
  logger.info('found artists: %s', s_artists)
  logger.info('found songs: %s', s_songs)
  logger.info('getting recs')
  recs = spot.get_recommendations(seed_genres=s_genres, seed_artists=s_artists, 
    seed_tracks=s_songs, attributes=s_attrs)
  if not recs:
    logger.info('no recs found')
    return ERROR_CODES.ERROR_NO_SPOTIFY_RECS, None
  track_uris = spot.tracksForRecs(recs)
  logger.info('track uris length: %s', len(track_uris))

  # find unique playlist. Re-prompt llm if none found
  pname = None
  with_retry = False
  while True:
    msgs = chat.create_playlist_name_from_query(user_query, with_retry=with_retry)
    if not using_cohere:
      pnames_list = chat.get_assistant_message(msgs, temperature=.5)
    else:
      pnames_list = cohere_lib.get_assistant_message(msgs, max_tokens=100)
    logger.info('llm output playlist list: %s', pnames_list)
    for name in chat.parse_playlist_name(pnames_list):
      if not spot.does_playlist_exist(name):
        pname = name
        logger.info('Playlist name: %s', pname)
        break
    if pname:
      break
    logger.info('no unique playlists found')
    with_retry = True

  # get playlist info
  playlist_id, playlist_url = spot.get_playlist_info(pname=pname)
  if playlist_id is None:
    logger.info('playlist id is none')
    return ERROR_CODES.ERROR_NO_PLAYLIST_CREATE, None
  spot.playlist_write_tracks(playlist_id, track_uris)
  logger.info('wrote tracks')
  logger.info('playlist url: %s', playlist_url)
  return ERROR_CODES.NO_ERROR, playlist_url


_ = '''
user_query = 'make me a playlist to get high to'
spot = spotify.SpotifyRequest()
spot.reinit()

genres = spot.get_genre_seeds()['genres']
attributes = spot.get_attributes()
msgs = chat.create_prompt(user_query, attrs=attributes, genres=genres)
prompt = [m['content'] for m in msgs]
prompt = '\n'.join(prompt)

import cohere
coapi = os.getenv('COHERE_TRIAL_API_KEY')
co = cohere.Client(coapi)
response = co.generate(
  prompt=prompt,
  model='xlarge',
  max_tokens=400,
  temperature=.9,
  k=0
  )
'''
