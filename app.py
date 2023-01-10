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

all_chars = "ABCDEFGHIJKLMONPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890_-"


@app.get('/')
def landing_page():
    username = request.cookies.get('username')
    if username:
        return redirect('/home')
    return render_template('landing.html')


@app.get('/home')
def home_page():
    username = request.cookies.get("username")
    if username:
        return render_template('home.html', username=username)
    else:
        return redirect("/")


@app.get('/logout')
def logout():
    response = redirect("/")
    response.set_cookie("username", "", expires=0)
    response.set_cookie('lobby', '', expires=0)
    return response


@app.post('/signup')
def register():
    username = escape_html(request.form['username'])
    pwd = request.form['password']
    if not valid_username(username):
        return "Invalid Username"
    if len(pwd) < 6 or len(pwd) > 20:
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
            response.set_cookie('lobby', '')
            return response


@app.post('/join-lobby')
def join_lobby():
    lobby_id = request.form['lobby_id']
    if lobby_id not in lobbies.keys():
        return "Lobby does not exist"
    else:
        username = request.cookies.get('username')
        lobbies[lobby_id].append(username)
        response = redirect(f'/lobby/{lobby_id}')
        response.set_cookie('lobby_id', lobby_id)
        response.set_cookie('dm', 'false')
        return response


@app.get('/lobby/<lobby_id>')
def lobby(lobby_id):
    if lobby_id in lobbies.keys():
        username = request.cookies.get('username')
        is_dm = request.cookies.get('dm')
        if username:
            if is_dm == 'true':
                return render_template('dm_lobby.html', id=lobby_id, user=username, async_mode="threading")
            else:
                lobbies[lobby_id].append(username)
                return render_template('lobby.html', id=lobby_id, user=username, async_mode="threading")
        else:
            return redirect('/')
    else:
        return "Invalid Lobby Code, please try again"


@app.get('/create-lobby')
def create_lobby():
    lobby_id = generate_lobby_id()
    username = request.cookies.get('username')
    if username:
        lobbies[lobby_id] = [username]
        response = redirect('/lobby/' + lobby_id)
        response.set_cookie('lobby_id', lobby_id)
        response.set_cookie('dm', 'true')
        return response
    else:
        return redirect('/')


def generate_lobby_id():
    return ''.join(random.choice("abcdefghiklmopqrstuvwxyz1234567890") for _ in range(6))


def escape_html(text):
    return text.replace('&', '&amp').replace('<', '&lt').replace('>', '&gt')


@socket.event()
def join(data):
    username = data['username']
    room_id = data['room']
    join_room(room_id)
    emit('message', f"{username} has joined!", to=room_id)


@socket.event()
def player_leave(data):
    room_id = data['room']
    username = data['username']
    lobbies[room_id].remove(username)
    emit('message', f"{username} left the lobby", to=room_id)
    leave_room(room_id)


@socket.event()
def dm_leave(data):
    room_id = data['room']
    emit('message', f"Lobby {room_id} is now closed", to=room_id)
    leave_room(room_id)
    del lobbies[room_id]
    emit('close', to=room_id)


@socket.event()
def message(data):
    room_id = data['room']
    if room_id not in lobbies.keys():
        emit('message', "Lobby does not exist")
    else:
        msg = escape_html(data['msg'])
        username = data['username']
        emit('message', f"{username}: {msg}", to=room_id)


def valid_username(username):
    for char in username:
        if char not in all_chars:
            return False
    if len(username) < 3 or len(username) > 20:
        return False
    return True


socket.run(app, allow_unsafe_werkzeug=True, debug=True)
