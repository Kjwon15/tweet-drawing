from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    oauth_token = Column(String(200))
    oauth_secret = Column(String(200))

    drawings = relationship('Drawing', backref='user',
                            cascade='all, delete-orphan')

    def __init__(self, user_id):
        self.user_id = user_id


class Drawing(Base):
    __tablename__ = 'drawings'
    status_id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey(User.user_id))
    tweet = Column(String(200))
    datetime = Column(DateTime(timezone=True), index=True)

    def __init__(self, status_id, tweet, datetime):
        self.status_id = status_id
        self.tweet = tweet
        self.datetime = datetime
