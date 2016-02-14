import datetime
import logging
import os
import random
import time

import schedule
import tweepy

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import Base, Drawing


engine = create_engine(os.environ.get('DATABASE_URL'))
session = scoped_session(sessionmaker(bind=engine))
Base.query = session.query_property()

CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')


def do_drawing(drawing):
    logger = logging.getLogger(__name__)
    user = drawing.user
    message = drawing.message

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(user.oauth_token, user.oauth_secret)
    api = tweepy.API(auth)

    logger.info('drwaing for {}'.format(drawing.status_id))

    cursor = tweepy.Cursor(api.retweeters, drawing.status_id)
    retweeters = list(cursor.items())
    if retweeters:
        chosen = random.choice(list(retweeters))
        retweeter = api.get_user(chosen)
        msg = message.format(
            user=retweeter.name, name=retweeter.screen_name)
    else:
        msg = 'Nobody has retweeted this.'

    msg = '{} #twtDraw https://filebo.xyz'.format(msg)

    api.update_status(
        status=msg,
        in_reply_to_status_id=drawing.status_id)


def draw_pending():
    now = datetime.datetime.utcnow()

    for drawing in Drawing.query.filter(Drawing.datetime <= now):
        try:
            do_drawing(drawing)
        except Exception as e:
            logger.error(e)
        else:
            session.delete(drawing)

    session.commit()
    session.close()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    schedule.every().minutes.do(draw_pending)
    schedule.run_all()
    while 1:
        schedule.run_pending()
        time.sleep(1)
