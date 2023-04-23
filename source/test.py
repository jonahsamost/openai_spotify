
from dotenv import load_dotenv
load_dotenv('/home/f2_user/Glorface/.config')

import os
from twilio.rest import Client
from ttdb import TTDB

tt = TTDB()

# tt._test_playlist_insert()
# out = tt.execute('select * from playlist')
# n = out[0][0]

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']
from twilio.rest import Client
client = Client(account_sid, auth_token)

# VCF_HOSTING_PATH = 'http://143.198.173.172:5000/reports/ThumbTings.vcf'
VCF_HOSTING_PATH = 'https://tt.thumbtings.com:4443/reports/ThumbTings.vcf'
THIS_NUMBER = '+16099084970'
message = client.messages.create(
  from_=THIS_NUMBER, to='+16093135446',
  media_url=[VCF_HOSTING_PATH])
