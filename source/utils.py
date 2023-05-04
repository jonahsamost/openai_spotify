
def is_playlist_intent(body: str) -> bool:
  """Given a user query, try to determine if the intent is to create a playlist."""
  bl = body.lower()
  if bl.startswith('create'):
    return True
  elif bl.startswith('make'):
    return True
  elif bl.find('playlist') != -1:
    return True
  elif bl.find('music') != -1:
    return True
  elif bl.find('songs') != -1:
    return True
  return False
