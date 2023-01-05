from flask import Flask, request, render_template, redirect
import firebase_admin
from flask_socketio import SocketIO, join_room, leave_room, emit
from firebase_admin import credentials, firestore
import random

cred = credentials.Certificate("config.json")
fb = firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)
socket = SocketIO(app)

# dict of lobby id to list of users in lobby
lobbies = {}

all_chars = "ABCDEFGHIJKLMONPQRSTUVWXYZabcdefghiklmopqrstuvwxyz1234567890_-"


@app.get('/')
def landing_page():
    return render_template('landing.html')


@app.get('/home')
def home_page():
    username = request.cookies.get("username")
    if username:
        return render_template('home.html', username=username)
    else:
        return redirect("/")


@app.post('/signup')
def register():
    username = escape_html(request.form['username'])
    pwd = request.form['password']
    if sum(c for c in username if c not in all_chars) > 0 or len(username) > 20:
        return "Invalid username"
    if len(pwd) < 8 or len(pwd) > 20:
        return "Invalid Password"
    users_ref = db.collection('users').where('username', '==', username)
    user = users_ref.get()
    if user:
        return "Username Taken"
    else:
        db.collection('users').add({
            'username': username,
            'password': pwd
        })
        return redirect('/')


@app.post('/login')
def login():
    username = escape_html(request.form['username'])
    pwd = request.form['password']

    users_ref = db.collection('users').where('username', '==', username)
    user = users_ref.get()
    if not user:
        return "Username or Password is Incorrect"
    else:
        if user[0].to_dict()['password'] != pwd:
            return redirect('/')
        else:
            response = redirect("/home")
            response.set_cookie('username', username)
            return response


@app.get('/lobby/<lobby_id>')
def join_lobby(lobby_id):
    if lobby_id in lobbies.keys():
        username = request.cookies.get('username')
        if username:
            lobbies[lobby_id].append(username)
            return render_template('lobby.html', id=lobby_id, user=username, async_mode="threading")
        else:
            return redirect('/')
    else:
        return "Invalid Lobby Code"


@app.get('/create-lobby')
def create_lobby():
    lobby_id = generate_lobby_id()
    username = request.cookies.get('username')
    if username:
        lobbies[lobby_id] = [username]
        return render_template('lobby.html', id=lobby_id, user=username, async_mode="threading")
    else:
        return redirect('/')


def generate_lobby_id():
    return ''.join(random.choice("abcdefghiklmopqrstuvwxyz1234567890") for _ in range(6))


def escape_html(text):
    """Returns a version of the input string with escaped html."""
    return text.replace('&', '&amp').replace('<', '&lt').replace('>', '&gt')


@socket.event()
def join(data):
    username = data['username']
    room_id = data['room']
    join_room(room_id)
    print(room_id, flush=True)
    emit('message', f"{username} has joined!", to=room_id)


@socket.event()
def message(data):
    room_id = data['room']
    msg = escape_html(data['msg'])
    username = data['username']
    emit('message', f"{username}: {msg}", to=room_id)


if __name__ == '__main__':
    socket.run(app, allow_unsafe_werkzeug=True, debug=True)
