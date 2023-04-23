import os
import psycopg2
from dataclasses import dataclass, asdict
from datetime import datetime as dt
import threading
from loglib import logger

db_user = os.environ['DB_USER']
db_pass = os.environ['DB_PASS']
db_name = os.environ['DB_NAME']

@dataclass
class BaseDC:
  def dict(self):
    return {k: str(v) for k, v in asdict(self).items()}

@dataclass
class Playlist(BaseDC):
  phone_number: str
  playlist_id: str
  prompt: str
  success: int
  time_created: dt
  error_message: str = ''

@dataclass
class Users(BaseDC):
  phone_number: str
  subscribed: int
  playlist_created: int

@dataclass
class UserMessages(BaseDC):
  phone_number: str
  message: str


class TTDB():
  def __init__(self):
    self.conn = psycopg2.connect(
      host='localhost', database=db_name,
      user=db_user, password=db_pass
    )
    self.cur = self.conn.cursor()
    self.lock = threading.Lock()
    self.playlist_table = 'playlist'
    self.user_table = 'users'
    self.user_messages = 'user_messages'
    self._create_tables()

  def close(self):
    self.cur.close()
    self.conn.close()

  def execute(self, cmd, *args):
    self.lock.acquire()
    try:
      self.cur.execute(cmd, args)
    except Exception as e:
      logger.info('DB exception: %s', e)

    self.conn.commit()
    self.lock.release()

    try:
      return self.cur.fetchall()
    except:
      return None

  def _create_tables(self):
    playlist = (
      f'create table if not exists {self.playlist_table} ('
        'phone_number varchar,'
        'playlist_id varchar (40),'
        'prompt varchar (300),'
        'success integer not null,'
        'time_created timestamp with time zone,'
        'error_message varchar (300)'
        ');'
    )
    self.execute(playlist)

    users = (
      f'create table if not exists {self.user_table} ('
        'phone_number varchar primary key,'
        'subscribed int,'
        'playlist_created int'
      ');'
    )
    self.execute(users)

    messages = (
      f'create table if not exists {self.user_messages} ('
        'phone_number varchar,'
        'message varchar (300)'
        ');'
    )
    self.execute(messages)

  def user_insert(self, args: dict):
    return self._table_insert(args, self.user_table)

  def user_message_insert(self, args: dict):
    return self._table_insert(args, self.user_messages)

  def playlist_insert(self, args: dict):
    return self._table_insert(args, self.playlist_table)

  def _table_insert(self, args: dict, table_name: str):
    keys = ', '.join(list(args.keys()))
    values_ph = ', '.join(['%s'] * len(args))
    insert = (
      f'insert into {table_name} ({keys})'
      f'values ({values_ph})'
    )
    return self.execute(insert, *list(args.values()))

  def get_user(self, phone_number: str) -> bool:
    q = f'select * from {self.user_table} where phone_number = %s'
    return self.execute(q, *[phone_number])

  def get_user_count(self) -> int:
    q = f'select count(*) from {self.user_table};'
    return self.execute(q)[0][0]

  def user_created_playlist(self, phone_number):
    q = (
      f'update {self.user_table} '
      'set playlist_created=1 '
      'where phone_number = %s;'
      )
    return self.execute(q, *[phone_number])

  def _test_playlist_insert(self):
    d = Playlist(
      phone_number = '+16093135446',
      playlist_id = '132EIn7jj8PsKw2AORasuS',
      prompt = 'make me a playlist "with" \'ambien\'t audio. music that will help me focus. super instrumental. study music but upbeat. high bpm. Similar to The Chemical Brothers or Justice or Fred again..',
      success = 1,
      time_created=dt.now(), 
      error_message= '')
    self.playlist_insert(d.dict())

    d = Users(
      phone_number='+16093135446', subscribed=1, playlist_created=0
    )
    self.user_insert(d.dict())

    d = UserMessages(
      phone_number='+16093135446', message='adfasdfasdfasd fuck'
    )
    self.user_message_insert(d.dict())
