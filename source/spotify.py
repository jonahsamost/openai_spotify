from loglib import logger
import json
import random
import re
import requests
import spotipy
import string
import time
import os
from flask import session
import base64



s_name = os.environ['SPOTIFY_NAME']
s_username = os.environ['SPOTIFY_USERNAME']
s_id = os.environ['SPOTIFY_ID']
s_secret = os.environ['SPOTIFY_SECRET']
s_redirect = os.environ['SPOTIFY_REDIRECT']

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
ME_URL = 'https://api.spotify.com/v1/me'

scope=[
    'playlist-read-private',
    'playlist-read-collaborative',
    'playlist-modify-private',
    'playlist-modify-public',
    'user-follow-read',
    'user-top-read',
    'user-read-recently-played',
    'user-library-read',
]

class SpotifyRequest(object):
    def __init__(self):
        super(SpotifyRequest, self).__init__()
        self._token = None
        self._base = 'https://api.spotify.com/v1/'
        self._session = requests.Session()
        self._username = None
        self._soa = None
        self._loc = 0

    def reauth(self):
        self._client_id = s_id
        self._secret = s_secret
        self._fname = s_name
        self._redirect = s_redirect
        self._username = s_username

        self._soa = spotipy.oauth2.SpotifyOAuth(client_id=self._client_id, 
            client_secret=self._secret, redirect_uri=self._redirect, 
            scope=self.scope)
        return 1

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, tok):
        self._token = tok

    @property
    def scope(self):
        return ' '.join(scope)

    @property
    def auth(self):
        assert self._token is not None, 'self._token is None'
        return {"Authorization": "Bearer {0}".format(self.token)}


    def reinit(self):
      def __tokes_init():
        self.reauth()
        tokes = None
        try:
          tokes = self._soa.get_cached_token()
        except:
          pass

        if not tokes:
          self._soa.get_access_token()
          tokes = self._soa.get_cached_token()

        return tokes

      tokes = __tokes_init()

      while 1:
        try:
          self._soa.refresh_access_token(tokes['refresh_token'])
          logger.info('Refreshing token!')
          break
        except Exception as e:
          logger.info('Reiniting token!')
          tokes = __tokes_init()

      tokes = self._soa.get_cached_token()
      self.token = tokes['access_token']

    def _call(self, method, url, args=None, payload=None, **kwargs):
      url = self._base + url
      while 1:
        headers = self.auth
        if method != 'POST':
          headers['Content-Type'] = 'application/json'

        try:
          if method == "GET":
            response = self._session.request(method, url, headers=headers, params=kwargs)
          elif method == "POST" or method == "PUT" or method == "DELETE":
            response = self._session.request(method, url, headers=headers, data=payload)
        except Exception as e:
          logger.info('Caught exception: %s', e)
          self._session = requests.Session()
          time.sleep(10)
          continue 

        if response.status_code in [200, 201]:
          try:
            return json.loads(response.text)
          except:
            return ''
        elif response.status_code == 429:
          sleep_time = response.headers['Retry-After']
          self.reinit()
        elif response.status_code == 504: # Service didnt reply before timeout
          time.sleep(2)
        else:
          logger.info(f"Error: {response.status_code}, {response.text}")
          return None

    def current_user(self):
      return self._call('GET', 'me/')

    def current_user_playlists(self, limit=50, offset=0):
      return self._call('GET', 'me/playlists', limit=limit, offset=offset)

    def get_genre_seeds(self):
      return self._call('GET', "recommendations/available-genre-seeds")

    def user_playlist_create(self, playlist_name, public=True, collaborative=False):
      payload = json.dumps({'name': playlist_name, 'public': public, 'collaborative': collaborative})
      return self._call('POST', f'users/{self._username}/playlists', payload=payload)

    def get_attributes(self):
      return [
        "acousticness", "danceability",
        "energy", "instrumentalness", "liveness", "loudness",
        "popularity", "speechiness"]

    def _search_tracks(self, artist, track):
      """try to return track id for artist, track pair."""
      soft_ids = []
      for i in range(2):
        result = self._call('GET', 'search', q=f'artist:{artist} track:{track}' , type='track', limit=50 , offset=i)
        for item in result['tracks']['items']:
          r_name = item['name'].lower()
          r_artists = [arts['name'].lower() for arts in item['artists']]
          if r_name == track.lower() and artist in r_artists:
            return item['id']
          elif r_name.find(track.lower()) != -1:
            if artist in r_artists:
              soft_ids.append(item['id'])
            elif any([r_art.lower().find(artist.lower()) != -1 for r_art in r_artists]):
              soft_ids.append(item['id'])
      return soft_ids[0] if soft_ids else None

    def IdsForSongs(self, search_terms: dict):
      """Finds artist ids for a given list of artists."""
      ids = []
      for track, artist in search_terms.items():
        track_id = self._search_tracks(artist, track)
        if track_id:
          ids.append(track_id)
      return ids if ids else None

    def _search_artists(self, artist):
      """Try to search for single artist."""
      soft_ids = []  # does search term appear in result?
      for i in range(2):
        result = self._call('GET', 'search', q=f'artist:{artist}' , type='artist', limit=50 , offset=i)
        for item in result['artists']['items']:
          name = item['name'].lower()
          if name == artist.lower():
            return item['id']
          if name.find(artist.lower()) != -1:
            soft_ids.append(item['id'])
      return soft_ids[0] if soft_ids else None

    def IdsForArtists(self, search_terms: list):
      """Finds artist ids for a given list of artists."""
      ids = []
      for term in list(set(search_terms)):
        artist = self._search_artists(term)
        if artist:
          ids.append(artist)
      return ids if ids else None

    def get_recommendations(self, limit=50, seed_artists=[], seed_tracks=[], seed_genres=[], attributes={}):
      attrs = self.get_attributes()
      params = {}
      cnt = 0
      
      # can only seed at most 5
      if seed_artists:
        included_artists = seed_artists[:5-cnt]
        params['seed_artists'] = ','.join(included_artists)
        cnt += len(included_artists)
      if seed_genres and cnt <= 5:
        included_genres = seed_genres[:5-cnt]
        params['seed_genres'] = ','.join(included_genres)
        cnt += len(included_genres)
      if seed_tracks and cnt <= 5:
        included_tracks = seed_tracks[:5-cnt]
        params['seed_tracks'] = ','.join(included_tracks)
      for a, v in attributes.items():
        if a in attrs:
          if a == 'popularity':
            rem = re.match('[0-9]*', v)
            if rem:
              val = int(rem.group())
              if val < 0: val = 0
              if val > 100: val = 100
            else:
              continue
          elif a == 'tempo':
            rem = re.match('[0-9]*', v)
            if rem:
              val = int(rem.group())
              if val < 50: val = 50
              if val > 260: val = 260
            else:
              continue
          else:
            val = re.match('[0-9]*', v)
            if not val:
              continue
            val = int(val.group()) / 100
            if val < 0: val = 0
            if val > 1: val = 1
          params[f'target_{a}'] = val
      params['limit'] = limit
      params['market'] = 'US' # only return us available stuff for now
      return self._call('GET', "recommendations", **params)

    def find_playlist_with_name(self, pname) -> dict:
      pname = bytes(pname, 'utf-8')
      pitems = self.current_user_playlists()
      for i in pitems['items']:
        name =  i['name'].encode('ascii', 'ignore')
        if name == pname:
          return i
      return {}

    def does_playlist_exist(self, pname: str):
      playlist_info = self.find_playlist_with_name(pname)
      return playlist_info.get('id', None)

    def create_playlist(self, pname: str):
      result = self.user_playlist_create(pname)
      if result is None:
        return None, None
      return result['id'], result['external_urls']['spotify']

    def playlist_write_tracks(self, playlist_id, track_uris):
      return self._call('POST', f'playlists/{playlist_id}/tracks', payload=json.dumps(track_uris), position=0)

    def playlist_by_id(self, playlist_id):
      return self._call('GET', f'playlists/{playlist_id}')

    def tracksForRecs(self, recs):
      return [track['uri'] for track in recs['tracks']]

    def playlist_make_private(self, playlist_id):
      new_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
      data = {'public': False, 'name': new_name}
      return self._call('PUT', f'playlists/{playlist_id}', payload=json.dumps(data)) 

    def playlist_get_track_uris(self, playlist_id) -> list:
      pinfo = self.playlist_by_id(playlist_id)
      if not pinfo:
        return []
      return [track['track']['uri'] for track in pinfo['tracks']['items']]

    def playlist_delete_tracks(self, playlist_id):
      track_uris = self.playlist_get_track_uris(playlist_id)
      if not track_uris:
        return
      data = {'tracks': [{'uri': uri} for uri in track_uris]}
      return self._call('DELETE', f'playlists/{playlist_id}/tracks', payload=json.dumps(data))
      


def chatOutputToStructured(txt, attributes=[], number_id: str = ''):
  attrs = {}
  genres = []
  artists = []
  songs = {}

  attributes = attributes + ['tempo']
  for val in txt.split('\n'):
    if not val:
      continue
    try:
      att, vals = val.split(':')
    except:
      continue
    if att.find('genres') != -1 and not genres:
      genres = vals
    elif att.find('artists') != -1 and not artists:
      artists = vals
    elif att.find('songs') != -1 and not songs:
      songs = vals
    elif att.strip() in attributes and att.strip() not in attrs:
      attrs[att.strip()] = vals.strip()

  if genres:
    logger.info('%s: found genres: %s', number_id, genres)
    genres = [g.strip() for g in genres.split(',')] 
  
  if artists:
    logger.info('%s: found artists: %s', number_id, artists)
    artists = [g.strip() for g in artists.split(',')] 

  song_artist_dic = {}
  if songs:
    logger.info('%s: found songs: %s', number_id, songs)
    for sa in songs.split(','):
      s_by_a = sa.split('by')
      if len(s_by_a) != 2:
        continue
      cur_song = s_by_a[0].replace('"', '').strip()
      cur_artist = s_by_a[1].strip()
      song_artist_dic[cur_song] = cur_artist
    logger.info('%s: filtered songs: %s', number_id, song_artist_dic)
  songs = song_artist_dic

  if not isinstance(artists, list): artists = list(artists)
  if not isinstance(genres, list): genres = list(genres)

  return genres, artists, songs, attrs


def spotify_refresh_token(refresh_token: str = ''):
  '''Refresh spotify access token.'''

  logger.info("Refreshing token")
  if refresh_token:
    token = refresh_token
  else:
    token = session.get('tokens').get('refresh_token')
  payload = {
    'grant_type': 'refresh_token',
    'refresh_token': token,
  }
  headers = {}
  headers['Content-Type'] = 'application/x-www-form-urlencoded'
  id_secret = bytes(s_id + ':' + s_secret, 'utf-8')
  basic = b'Basic ' + base64.b64encode(id_secret)
  headers['Authorization'] = basic.decode('utf-8')

  res = requests.post(
    TOKEN_URL,
    data=payload,
    headers=headers
  )
  res_data = res.json()

  # Load new token into session
  access_token = res_data.get('access_token')
  if not refresh_token:
    session['tokens']['access_token'] = access_token
  return access_token

