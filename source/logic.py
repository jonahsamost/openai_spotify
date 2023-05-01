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
  ERROR_SPOTIFY_REFRESH=7

def playlist_for_query(user_query: str,
    number_id: str,
    token: str = ''):
  """Responds with tuple of (Error, Message)."""
  spot = spotify.SpotifyRequest()
  if token:
    spot.token = token
    spot._tt_user = True
    cuser = spot.current_user()
    if cuser is None:
      spotify.spotify_refresh_token()
      cuser = spot.current_user()
      # try to refresh
      if cuser is None:
        return ERROR_CODES.ERROR_SPOTIFY_REFRESH, None

    spot._username = cuser['id']
    logger.info('current spotify user: %s', cuser['id'])
  else:
    spot.reinit()
    if not spot.current_user():
      return ERROR_CODES.ERROR_NO_SPOTIFY_USER, None

  genres = spot.get_genre_seeds()['genres']
  with open('/tmp/genres', 'w') as fd:
    fd.write('\n'.join(genres))
  attributes = spot.get_attributes()
  msgs = chat.create_prompt(user_query, attrs=attributes, genres=genres)

  chat_outputs = chat.get_assistant_message(msgs, number_id=number_id)
  if not chat_outputs:
    return ERROR_CODES.ERROR_CHAT_GPT, None
  logger.info('%s: openai output: %s', number_id, chat_outputs)
  using_cohere = False
  s_genres, s_artists, s_songs, s_attrs = spotify.chatOutputToStructured(
    chat_outputs, attributes=attributes, number_id=number_id)

  # could openai successfully generate?
  # try with cohere if not
  if not any([s_genres, s_artists, s_songs, s_attrs]):
    chat_outputs = cohere_lib.get_assistant_message(msgs, number_id=number_id)
    logger.info('%s: cohere output: %s', number_id, chat_outputs)
    if not chat_outputs:
      return ERROR_CODES.ERROR_COHERE_GEN, None
    s_genres, s_artists, s_songs, s_attrs = spotify.chatOutputToStructured(
      chat_outputs, attributes=attributes, number_id=number_id)
    if not any([s_genres, s_artists, s_songs, s_attrs]):
      return ERROR_CODES.ERROR_NO_GEN, None
    using_cohere = True

  s_artists = s_artists + list(s_songs.values())
  logger.info('%s: before genres: %s', number_id, s_genres)
  s_genres = [g for g in s_genres if g in genres]
  logger.info('%s: after genres: %s', number_id, s_genres)
  logger.info('%s: artists: %s', number_id, s_artists)
  logger.info('%s: songs: %s', number_id, s_songs)
  logger.info('%s: attributes: %s', number_id, s_attrs)
  s_artists = spot.IdsForArtists(s_artists)
  s_songs = spot.IdsForSongs(s_songs)
  logger.info('%s: found artists: %s', number_id, s_artists)
  logger.info('%s: found songs: %s', number_id, s_songs)
  recs = spot.get_recommendations(seed_genres=s_genres, seed_artists=s_artists, 
    seed_tracks=s_songs, attributes=s_attrs)
  if not recs:
    logger.info('%s: no recs found', number_id)
    return ERROR_CODES.ERROR_NO_SPOTIFY_RECS, None
  track_uris = spot.tracksForRecs(recs)
  logger.info('%s: track uris length: %s', number_id, len(track_uris))

  # find unique playlist. Re-prompt llm if none found
  pname = None
  with_retry = False
  while True:
    msgs = chat.create_playlist_name_from_query(user_query, with_retry=with_retry)
    if not using_cohere:
      pnames_list = chat.get_assistant_message(msgs, temperature=.5, number_id=number_id)
    else:
      pnames_list = cohere_lib.get_assistant_message(msgs, max_tokens=100, number_id=number_id)
    logger.info('%s: llm output playlist list: %s', number_id, pnames_list)
    for name in chat.parse_playlist_name(pnames_list):
      if not spot.does_playlist_exist(name):
        pname = name
        logger.info('%s: Playlist name: %s', number_id, pname)
        break
    if pname:
      break
    logger.info('%s: no unique playlists found', number_id)
    with_retry = True

  # get playlist info
  playlist_id, playlist_url = spot.create_playlist(pname=pname)
  if playlist_id is None:
    logger.info('%s: playlist id is none', number_id)
    return ERROR_CODES.ERROR_NO_PLAYLIST_CREATE, None
  spot.playlist_write_tracks(playlist_id, track_uris)
  logger.info('%s: playlist url: %s', number_id, playlist_url)
  return ERROR_CODES.NO_ERROR, playlist_url


