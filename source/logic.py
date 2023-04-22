import chat
import spotify
import argparse
import sys
from loglib import logger
from enum import Enum

class ERROR_CODES(Enum):
  NO_ERROR=0
  ERROR_NO_SPOTIFY_USER=1
  ERROR_CHAT_GPT=2
  ERROR_NO_SPOTIFY_RECS=3
  ERROR_NO_PLAYLIST_CREATE=4
  ERROR_OPENAI_SEX=5

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
  logger.info('gpt output: %s', chat_outputs)
  s_genres, s_artists, s_songs, s_attrs = spotify.chatOutputToStructured(chat_outputs, attributes=attributes)
  if not any([s_genres, s_artists, s_songs, s_attrs]):
    return ERROR_CODES.ERROR_OPENAI_SEX, None
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
    pnames_list = chat.get_assistant_message(msgs, temperature=.5)
    logger.info('llm output playlist list: %s', pnames_list)
    for name in chat.parse_playlist_name(pnames_list):
      if not spot.does_playlist_exist(name):
        pname = name
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


query = 'Make me a playlist of ambient electronic music with some latin flare and sprinkle in some country with a little energy and not very loud but with pop. Similar to Daft Punk or Jon Hopkins or drone logic by Daniel Avery.'
spot = spotify.SpotifyRequest()
spot.reinit()
