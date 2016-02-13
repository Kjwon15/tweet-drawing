import os

from flask import Flask, request, redirect, url_for, session, flash, g, \
    render_template
from flask_oauth import OAuth

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import Base, User

app = Flask(__name__)
oauth = OAuth()

app.config.update({
    'DATABASE_URL': os.environ.get('DATABASE_URL', 'sqlite:///:memory:'),
    'SECRET_KEY': os.environ.get('SECRET_KEY', 'demo'),
})

twitter = oauth.remote_app(
    'twitter',
    base_url='https://api.twitter.com/1.1/',
    request_token_url='https://api.twitter.com/oauth/request_token',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authenticate',
    consumer_key=os.environ.get('CONSUMER_KEY'),
    consumer_secret=os.environ.get('CONSUMER_SECRET'),
)

db_session = None


@app.before_first_request
def init():
    global db_session
    engine = create_engine(app.config.get('DATABASE_URL'))
    db_session = scoped_session(sessionmaker(bind=engine))
    Base.query = db_session.query_property()
    Base.metadata.create_all(bind=engine)


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])


@app.after_request
def after_request(response):
    db_session.remove()
    return response


@twitter.tokengetter
def get_twitter_token():
    user = g.user
    if user is not None:
        return user.oauth_token, user.oauth_secret


@app.route('/oauth-authorized')
@twitter.authorized_handler
def oauth_authorized(resp):
    next_url = request.args.get('next') or url_for('index')
    if resp is None:
        flash('You denied the request to sign in.')
        return redirect(next_url)

    user = User.query.get(resp['user_id'])
    if user is None:
        # First time sign in
        user = User(resp['user_id'])
        db_session.add(user)

    user.oauth_token = resp['oauth_token']
    user.oauth_secret = resp['oauth_token_secret']
    db_session.commit()

    session['user_id'] = user.user_id
    flash('Signed in.')
    return redirect(next_url)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    callback_url = url_for(
        'oauth_authorized',
        next=request.args.get('next') or request.referrer or None)
    return twitter.authorize(callback=callback_url)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You were signed out')
    return redirect(request.referrer or url_for('index'))


if __name__ == '__main__':
    app.debug = True
    app.run()
