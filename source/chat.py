import os
import openai
import re
from typing import Dict, List, Union
import time
from loglib import logger

openai.api_key = os.getenv("OPENAI_API_KEY")
assert openai.api_key, 'No openai key'

def get_assistant_message(
  messages: List[Dict[str, str]],
  temperature: int = 0,
  model: str = "gpt-3.5-turbo",
  number_id: str = '') -> str:
  for i in range(3):
    try:
      res = openai.ChatCompletion.create(
        model=model,
        temperature=temperature,
        messages=messages
      )
      return res['choices'][0]['message']['content']
    except Exception as e:
      logger.info('%s: Open AI Exception: %s', number_id, e)
      time.sleep(2)


def _set_role_text(msgs: list = [], query: str = '', role: str = 'user'):
  m = {'role': role, 'content': query}
  msgs.append(m)


def pprint_msgs(msgs):
  logger.info('Pretty print msgs')
  for msg in msgs:
    content = msg['content']
    role = msg['role']
    logger.info(f'role: {role}')
    for m in content.split('\n'):
      logger.info(f'{m}')


def parse_playlist_name(llm_output: str) -> Union[list, None]:
  '''Parses llm output for playlist name.'''
  return re.findall('"(.*?)"', llm_output)


def create_playlist_name_from_query(user_req, with_retry=False):
  msgs = []

  prompt = 'You create 10 unique, interesting and fun 5 word playlists from a user query with one on each line of output. The playlist name is between double quotes. Be creative.'
  _set_role_text(msgs, query=prompt, role='system')

  prompt = ('"Latin Rhythms in Electronic Spaces"\n'
  '"Electronic Enchantment with a Country Twist""\n'
  '"Ambient Pop with Latin Grooves"\n'
  '"Electronic Rancheras under Starry Skies"\n'
  '"Chill Country with Electro Beats"')
  query = 'Make me a playlist of ambient electronic music with some latin flare and sprinkle in some country with a little energy and not very loud but with pop. Similar to Daft Punk or Jon Hopkins or drone logic by Daniel Avery.'
  _set_role_text(msgs, query=query, role='user')
  _set_role_text(msgs, query=prompt, role='assistant')

  prompt = ('"Synthwave Power Hour"\n'
  '"Energetic Electronica Workout Mix"\n'
  '"High-Octane Synth Attack"\n'
  '"Futuristic Synth Pump-Up Playlist"\n'
  '"Synth-Heavy Gym Motivation Mix"')
  query = 'Playlist with electronic with heavy synth. not lyrical. not popular. high energy. Like Deadmau5'
  _set_role_text(msgs, query=query, role='user')
  _set_role_text(msgs, query=prompt, role='assistant')

  if with_retry:
    user_req = 'The names you just returned were not creative enough. Try again:\n' + user_req

  _set_role_text(msgs, query=user_req, role='user')
  return msgs

def create_prompt(user_req, attrs='', genres=''):
  # Each attribute can be in the set: [acousticness, danceability, duration_ms, energy, instrumentalness, liveness, loudness, popularity, speechiness, tempo]
  # Each genre can be in the set [acoustic, afrobeat, alt-rock, alternative, ambient, anime, black-metal, bluegrass, blues, bossanova, brazil, breakbeat, british, cantopop, chicago-house, children, chill, classical, club, comedy, country, dance, dancehall, death-metal, deep-house, detroit-techno, disco, disney, drum-and-bass, dub, dubstep, edm, electro, electronic, emo, folk, forro, french, funk, garage, german, gospel, goth, grindcore, groove, grunge, guitar, happy, hard-rock, hardcore, hardstyle, heavy-metal, hip-hop, holidays, honky-tonk, house, idm, indian, indie, indie-pop, industrial, iranian, j-dance, j-idol, j-pop, j-rock, jazz, k-pop, kids, latin, latino, malay, mandopop, metal, metal-misc, metalcore, minimal-techno, movies, mpb, new-age, new-release, opera, pagode, party, philippines-opm, piano, pop, pop-film, post-dubstep, power-pop, progressive-house, psych-rock, punk, punk-rock, r-n-b, rainy-day, reggae, reggaeton, road-trip, rock, rock-n-roll, rockabilly, romance, sad, salsa, samba, sertanejo, show-tunes, singer-songwriter, ska, sleep, songwriter, soul, soundtracks, spanish, study, summer, swedish, synth-pop, tango, techno, trance, trip-hop, turkish, work-out, world-music] 
  prompt = f'''
  You are an expert at following exact directions.
  Return the 4 most likely genres, named artists, and named songs, and one number between 0 and 100 for each attribute.
  Each attribute can be in the set: {attrs}
  Each genre can be in the set {genres}
  Only list artists if the input contains an artist name.
  Only list songs if the input contains a song name.
  Think carefully about the attribute values.
  
  '''

  msgs = []
  _set_role_text(msgs, query=prompt, role='system')

  query = 'Make me a playlist of ambient electronic music with some latin flare and sprinkle in some country with a little energy and not very loud but with pop. Similar to Daft Punk or Jon Hopkins or drone logic by Daniel Avery or body by loud luxury'
  _set_role_text(msgs, query=query, role='user')
  output = '''
  genres: ambient, electronic, latin, country
  artists: Daft Punk, Jon Hopkins, Daniel Avery, Loud Luxury
  songs: "drone logic" by daniel avery, "body" by loud luxury
  acousticness: 25
  danceability: 75
  energy: 80
  instrumentalness: 25
  liveness: 75
  loudness: 40
  popularity: 80
  speechiness: 40
  tempo: 120
  '''
  _set_role_text(msgs, query=output, role='assistant')

  query = "Make me a playlist with electronic with heavy synth. not lyrical. not popular. high energy. Like Deadmau5's the veldt"
  _set_role_text(msgs, query=query, role='user')
  output = '''
  genres: electronic, synth-pop, deep-house
  artists: Deadmau5
  songs: "the veldt" by Deadmau5
  acousticness: 10
  danceability: 75
  energy: 80
  instrumentalness: 40
  liveness: 75
  loudness: 40
  popularity: 80
  speechiness: 0
  tempo: 140
  '''
  _set_role_text(msgs, query=output, role='assistant')

  query = 'Make me a musical playlist that conforms to: country'
  _set_role_text(msgs, query=query, role='user')
  output = '''
  genres: country, bluegrass
  artists:
  songs:
  acousticness: 50
  danceability: 50
  energy: 50
  instrumentalness: 50
  liveness: 50
  loudness: 50
  popularity: 50
  speechiness:50
  tempo: 150
  '''
  _set_role_text(msgs, query=output, role='assistant')

  _set_role_text(msgs, query=user_req, role='user')
  return msgs

