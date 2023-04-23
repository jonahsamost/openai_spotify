from dotenv import load_dotenv
load_dotenv('/home/f2_user/Glorface/.config')
from twilio_lib import app 
import ttdb

if __name__ == '__main__':
  db = ttdb.TTDB()
  db.close()
  app.run()
