import flask
import flask_login

login_manager = flask_login.LoginManager()
login_manager.session_protection = "strong"
users = {'user': {'pw': 'changos!'}}


class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    if email not in users:
        return

    user = User()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    email = request.form.get('user')
    if email not in users:
        return

    user = User()
    user.id = email

    # todo: DO NOT ever store passwords in plaintext and always compare password hashes using constant-time comparison!
    user.is_authenticated = request.form['pw'] == users[email]['pw']
    return user


@login_manager.unauthorized_handler
def unauthorized_handler():
    return '<meta http-equiv="refresh" content="3;url=/login"/>Unauthorized access. Redirecting to login in 3 seconds'


def login():
    if flask.request.method == 'GET':
        return flask.render_template('login.html')

    passw = flask.request.form['user']
    if passw in users:
        if flask.request.form['pw'] == users[passw]['pw']:
            user = User()
            user.id = passw
            flask_login.login_user(user, remember=False)
            return flask.redirect(flask.url_for('protected'))
    return 'Incorrect username/password'


def logout():
    flask_login.logout_user()
    return '<meta http-equiv="refresh" content="3;url=/"/>Logged out, redirecting to root'


@flask_login.login_required
def protected():
    return '<meta http-equiv="refresh" content="3;url=/"/>Logged in as: ' + flask_login.current_user.id + '<p>Redirecting in 3 seconds....</p>'