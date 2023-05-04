
from dotenv import load_dotenv
load_dotenv('/home/f2_user/Glorface/.config')

import os
import json
from twilio.rest import Client
from ttdb import TTDB
import ttdb
from datetime import datetime as dt

import spotify

tt = TTDB()

# tt._test_playlist_insert()
# out = tt.execute('select * from playlist')
# n = out[0][0]

# account_sid = os.environ['TWILIO_ACCOUNT_SID']
# auth_token = os.environ['TWILIO_AUTH_TOKEN']
# from twilio.rest import Client
# client = Client(account_sid, auth_token)

# # VCF_HOSTING_PATH = 'http://143.198.173.172:5000/reports/ThumbTings.vcf'
# VCF_HOSTING_PATH = 'https://tt.thumbtings.com/reports/ThumbTings.vcf'
# THIS_NUMBER = '+16099084970'
# message = client.messages.create(
#   from_=THIS_NUMBER, to='+16093135446',
#   media_url=[VCF_HOSTING_PATH])



# name = 'Irish-Sudanese Stereotypes-Based Aggression Motivation Mix'
# pinfo = spot.find_playlist_with_name(name)
# pid = pinfo['id']
# headers = spot.auth
# 
# spot.playlist_delete_tracks(pid)

# headers['Content-Type'] = 'application/json'
# url = spot._base + f'playlists/{pid}'
# response = spot._session.request('GET', url, headers=headers)
# 
# pinfo = json.loads(response.text)

# track_uris = spot.playlist_get_track_uris(pid)
# url = spot._base + f'playlists/{pid}/tracks'
# data = {'tracks': [{'uri': uri} for uri in track_uris]}
# response = spot._session.request('DELETE', url, headers=headers, data=json.dumps(data))
# 
# print(response.status_code)

# from twilio_lib import _send_vcf_msg
# 
# db = tt
# q = f'select * from {db.user_table} where playlist_created=1 and contact_sent=0'
# results = db.execute(q)
# result = results[0]
# user = ttdb.Users(*result)
# phone_number = user.phone_number
# 
# _send_vcf_msg(phone_number)

susers = tt.execute('select * from spotify_users')
js = ttdb.SpotifyCreds(*susers[0])
spot = spotify.SpotifyRequest()
spot.token = js.access_token

