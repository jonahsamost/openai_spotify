import requests
import spotipy
import json
import time

spotify_creds = {
  'name':'d',
  'id':'44d51995a3694b4c94c6e720584e0552',
  'secret':'329ee2f428124bca93b554a07b53d3f7',
}

class SpotifyRequest(object):
    def __init__(self, username='jsamost'):
        super(SpotifyRequest, self).__init__()
        self._token = None
        self._base = 'https://api.spotify.com/v1/'
        self._session = requests.Session()
        self._username = username
        self._soa = None

        self._loc = 0
        # self.reinit()

    def reauth(self):
        self._client_id = spotify_creds['id']
        self._secret = spotify_creds['secret']
        self._fname = spotify_creds['name']
        self._redirect = 'https://jasvandy.github.io/'

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
        scope = [
            'user-read-private',
            'user-follow-read',
            'user-library-read',
            'user-top-read',
            'user-read-recently-played',
            'playlist-modify-private',
            'playlist-read-private',
            'playlist-modify-public'
        ]
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
          print('Refreshing token!')
          break
        except Exception as e:
          print('Reiniting token!')
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
          elif method == "POST":
            response = self._session.request(method, url, headers=headers, data=payload)
        except Exception as e:
          print('Caught exception: ', e)
          self._session = requests.Session()
          time.sleep(10)
          continue 

        if response.status_code in [200, 201]:
          return json.loads(response.text)
        elif response.status_code == 429:
          sleep_time = response.headers['Retry-After']
          self.reinit()
        else:
          print(f"Error: {response.status_code}, {response.text}")
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

    def artistIdForName(self, artist_names):
      # TODO 

      artist_ids = []
      for artist in artist_names:
        result = self._call('GET', 'search', q=f'artist:{artist}' , type='artist', limit = 50 , offset = 0)
        for a in result['artists']['items']:
          if a['name'].lower() == artist.lower():
            artist_ids.append(a['id'])
            break
      return artist_ids if artist_ids else None
      return None

    def get_recommendations(self, limit=50, seed_artists=None, seed_tracks=None, seed_genres=None, attributes={}):
      attrs = self.get_attributes()
      params = {}
      cnt = 0

      if seed_artists: # list of artist_ids
        params['seed_artists'] = ','.join(seed_artists[:5-cnt])
        cnt += len(seed_artists)
      if seed_tracks:
        params['seed_tracks'] = ','.join(seed_tracks)
      if seed_genres:
        params['seed_genres'] = ','.join(seed_genres[:5-cnt])
      for a, v in attributes.items():
        if a in attrs:
          if a == 'popularity':
            val = int(v)
            if val < 0: val = 0
            if val > 100: val = 100
          else:
            val = int(v) / 100
            if val < 0: val = 0
            if val > 1: val = 1
          params[f'target_{a}'] = val
      params['limit'] = limit
      return self._call('GET', "recommendations", **params)

    def find_playlist_with_name(self, pname):
      pitems = self.current_user_playlists()
      for i in pitems['items']:
        name =  i['name'].encode('ascii', 'ignore')
        if name == pname:
          return i['id']
      return None

    ''' get playlist id for given name, make new one if name doesnt exist'''
    def get_playlist_id(self, pname='deejay'):
      playlist_id = self.find_playlist_with_name(pname)
      if playlist_id:
        return playlist_id
      result = self.user_playlist_create(pname)
      assert result, 'No playlist created'
      return result['id']

    def playlist_write_tracks(self, playlist_id, track_uris):
      return self._call('POST', f'playlists/{playlist_id}/tracks', payload=json.dumps(track_uris), position=0)
      # spot._call('POST', f'playlists/{playlist_id}/tracks', payload=track_ids, position=0)

    def tracksForRecs(self, recs):
      return [track['uri'] for track in recs['tracks']]


def chatOutputToStructured(txt, attributes=[]):
  attrs = {}
  genres = ''

  for val in txt.split('\n'):
    if not val:
      continue
    try:
      att, vals = val.split(':')
    except:
      return None, None
    if att.find('genres') != -1:
      genres = vals
    elif att.find('artists') != -1:
      artists = vals
    elif att.strip() in attributes:
      attrs[att.strip()] = vals.strip()

  if genres:
    genres = [g.strip() for g in genres.split(',')] 
  
  if artists:
    artists = [g.strip() for g in artists.split(',')] 

  return genres, artists, attrs
