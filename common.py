import logging as log

from dotenv import load_dotenv

load_dotenv()
log.basicConfig(level=log.INFO)
log = log.getLogger(__name__)
