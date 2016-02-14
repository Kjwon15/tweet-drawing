import datetime
import os
import random

import tweepy

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import Base, Drawing


engine = create_engine(os.environ.get('DATABASE_URL'))
session = scoped_session(sessionmaker(bind=engine))
Base.query = session.query_property()

CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')


def draw_pending():
    now = datetime.datetime.utcnow()

    for drawing in Drawing.query.filter(Drawing.datetime <= now):
        user = drawing.user
        message = drawing.message

        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(user.oauth_token, user.oauth_secret)
        api = tweepy.API(auth)

        print('{}: {}'.format(api.me().screen_name, message))

        cursor = tweepy.Cursor(api.retweeters, drawing.status_id)
        retweeters = list(cursor.items())
        if retweeters:
            chosen = random.choice(list(retweeters))
            retweeter = api.get_user(chosen)
            print(message.format(user=retweeter.name, name=retweeter.screen_name))
        else:
            print('Nobody has retweeted this.')


if __name__ == '__main__':
    draw_pending()
