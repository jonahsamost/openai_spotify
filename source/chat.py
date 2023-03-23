import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def sendChatCompletionWithMessage(msg, role='user', model='gpt-3.5-turbo', **kwargs):
  '''
  Sends a message and returns result using this endpoint
  https://platform.openai.com/docs/api-reference/chat
  Args:
   msg: str
  
  Returns: List of messages
  '''
  completion = openai.ChatCompletion.create(
    model=model,
    messages=[
      {"role": role,
      "content": msg}
    ],
    **kwargs
  )
  return [cc.message for cc in completion.choices]

# sendChatCompletionWithMessage('when was george bush senior born?', n=3, max_tokens=20)

def createPrompt(user_req, attrs='', genres=''):
  # Each attribute can be in the set: [acousticness, danceability, duration_ms, energy, instrumentalness, liveness, loudness, popularity, speechiness]
  # Each genre can be in the set [acoustic, afrobeat, alt-rock, alternative, ambient, anime, black-metal, bluegrass, blues, bossanova, brazil, breakbeat, british, cantopop, chicago-house, children, chill, classical, club, comedy, country, dance, dancehall, death-metal, deep-house, detroit-techno, disco, disney, drum-and-bass, dub, dubstep, edm, electro, electronic, emo, folk, forro, french, funk, garage, german, gospel, goth, grindcore, groove, grunge, guitar, happy, hard-rock, hardcore, hardstyle, heavy-metal, hip-hop, holidays, honky-tonk, house, idm, indian, indie, indie-pop, industrial, iranian, j-dance, j-idol, j-pop, j-rock, jazz, k-pop, kids, latin, latino, malay, mandopop, metal, metal-misc, metalcore, minimal-techno, movies, mpb, new-age, new-release, opera, pagode, party, philippines-opm, piano, pop, pop-film, post-dubstep, power-pop, progressive-house, psych-rock, punk, punk-rock, r-n-b, rainy-day, reggae, reggaeton, road-trip, rock, rock-n-roll, rockabilly, romance, sad, salsa, samba, sertanejo, show-tunes, singer-songwriter, ska, sleep, songwriter, soul, soundtracks, spanish, study, summer, swedish, synth-pop, tango, techno, trance, trip-hop, turkish, work-out, world-music] 
  prompt = f'''
  Given the user input, you will fill in Example 3 similar to Example 1 and Example 2 below. Return the 4 most likely genre, named artists, and a number from 0 to 100 for each attribute.
  Each attribute can be in the set: {attrs}
  Each genre can be in the set {genres}
  Only list artists if the input contains the artist name.

  Example 1:
  Input: Make me a playlist of ambient electronic music with some latin flare and sprinkle in some country with a lot of energy and not very loud but with pop. Similar to Daft Punk or Jon Hopkins.
  genres: ambient, electronic, latin, country
  artists: Daft Punk, Jon Hopkins
  acousticness: 25
  danceability: 75
  energy: 80
  instrumentalness: 25
  liveness: 75
  loudness: 40
  popularity: 80
  speechiness: 40

  Example 2:
  Input: Playlist with electronic with heavy synth. not lyrical. not popular. high energy. Like Deadmau5 
  genres: electronic, synth-pop, deep-house
  artists: Deadmau5
  acousticness: 10
  danceability: 75
  energy: 80
  instrumentalness: 40
  liveness: 75
  loudness: 40
  popularity: 80
  speechiness: 0

  Example 3:
  Input: {user_req}
  '''
  return prompt

