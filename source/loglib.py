import logging

logger = logging.getLogger('TT')
logging.basicConfig(
  format="[%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s", 
  level=logging.INFO)

