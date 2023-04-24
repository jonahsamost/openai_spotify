from dotenv import load_dotenv
load_dotenv('/home/f2_user/Glorface/.config')
from twilio_lib import app 
import twilio_lib
import ttdb
import time
import threading


if __name__ == '__main__':
  db = ttdb.TTDB()
  db.close()
  app.run()
