import os

import datetime

from flask import Flask, jsonify, request, redirect, url_for, session, flash, g, \
    render_template
from flask_oauth import OAuth

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import Base, Drawing, User

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


def get_embed_tweet(status_id):
    resp = twitter.get('statuses/oembed.json', data={
        'id': status_id,
        'align': 'center',
    })

    if resp.status == 200:
        return resp.data['html']

    return 'Invalid tweet'


app.jinja_env.filters['get_embed_tweet'] = get_embed_tweet


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
    drawings = None

    if g.user:
        drawings = Drawing.query.filter(Drawing.user == g.user)
    return render_template('index.html', drawings=drawings)


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


@app.route('/make-drawing', methods=['POST'])
def make_drawing():
    try:
        tweet = request.form.get('tweet')
        message = request.form.get('message')
        period = request.form.get('period')
    except KeyError as e:
        flash('Please complete the form. {}'.format(e))
        return redirect(request.referrer)
    else:
        resp = twitter.post('statuses/update.json', data={
            'status': tweet
        })
        if resp.status != 200:
            for error in resp.data['errors']:
                flash(error['message'])
            return redirect(request.referrer)

        if period == '24h':
            endtime = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        elif period == '48h':
            endtime = datetime.datetime.utcnow() + datetime.timedelta(hours=48)

        drawing = Drawing(resp.data['id'], message, endtime)
        drawing.user = g.user
        db_session.add(drawing)
        db_session.commit()

    return redirect(url_for('index'))


@app.route('/delete-drawing', methods=['DELETE'])
def delete_drawing():
    try:
        status_id = request.form.get('status_id')
    except KeyError:
        flash('Status id error')
        return redirect(request.referrer)
    else:
        drawing = Drawing.query.get(status_id)
        if drawing is None or drawing.user != g.user:
            flash('Invalid status id')
            return redirect(request.referrer)

        db_session.delete(drawing)
        db_session.commit()

    return jsonify({
        'status': 'success',
    })


if __name__ == '__main__':
    app.debug = True
    app.run()
