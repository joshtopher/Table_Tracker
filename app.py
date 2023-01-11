from flask import Flask, request, render_template, redirect
import firebase_admin
from flask_socketio import SocketIO, join_room, leave_room, emit
from firebase_admin import credentials, firestore
import random
import time

cred = credentials.Certificate("config.json")
fb = firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)
socket = SocketIO(app)

# dict of table id to list of users in table
tables = {}

all_chars = "ABCDEFGHIJKLMONPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890_-"


@app.get('/')
def landing_page():
    username = request.cookies.get('username')
    if username:
        response = redirect('/home')
        response.set_cookie('table', '')
        response.set_cookie('gm', 'false')
        return response
    return render_template('landing.html')


@app.get('/home')
def home_page():
    username = request.cookies.get("username")
    table_id = request.cookies.get("table")
    if username:
        if table_id != "":
            response = redirect('/home')
            response.set_cookie('table', '')
            response.set_cookie('gm', 'false')
            return response
        return render_template('home.html', username=username)
    else:
        return redirect("/")


@app.get('/logout')
def logout():
    response = redirect("/")
    response.set_cookie("username", "", expires=0)
    response.set_cookie('table', '', expires=0)
    response.set_cookie('gm', 'false', expires=0)
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
            response.set_cookie('table', '')
            return response


@app.post('/join-table')
def join_table():
    table_id = request.form['table_id']
    if table_id not in tables.keys():
        return "table does not exist"
    else:
        response = redirect(f'/table/{table_id}')
        response.set_cookie('table_id', table_id)
        response.set_cookie('gm', 'false')
        return response


@app.get('/table/<table_id>')
def table(table_id):
    if table_id in tables.keys():
        username = request.cookies.get('username')
        is_gm = request.cookies.get('gm')
        if username:
            tables[table_id].append(username)
            if is_gm == 'true':
                return render_template('dm_lobby.html', id=table_id, user=username, async_mode="threading")
            else:
                return render_template('lobby.html', id=table_id, user=username, async_mode="threading")
        else:
            return redirect('/home')
    else:
        return "Invalid table Code, please try again"


@app.get('/create-table')
def create_table():
    table_id = generate_table_id()
    username = request.cookies.get('username')
    if username:
        tables[table_id] = []
        response = redirect(f'/table/{table_id}')
        response.set_cookie('table_id', table_id)
        response.set_cookie('gm', 'true')
        return response
    else:
        return redirect('/home')


def generate_table_id():
    return ''.join(random.choice("abcdefghiklmopqrstuvwxyz1234567890") for _ in range(6))


def escape_html(text):
    return text.replace('&', '&amp').replace('<', '&lt').replace('>', '&gt')


@socket.event()
def join(data):
    table_id = data['table']
    join_room(table_id)


@socket.event()
def player_leave(data):
    table_id = data['table']
    username = data['username']
    tables[table_id].remove(username)
    time.sleep(1)
    if username not in tables[table_id]:
        emit('message', f"{username} left the table", to=table_id)
        leave_room(table_id)


@socket.event()
def gm_leave(data):
    table_id = data['table']
    username = data['username']
    if table_id in tables.keys():
        tables[table_id].remove(username)
    time.sleep(1)
    if username not in tables[table_id]:
        emit('message', f"table {table_id} is now closed", to=table_id)
        emit('close', to=table_id)
        leave_room(table_id)
        del tables[table_id]


@socket.event()
def message(data):
    table_id = data['table']
    if table_id not in tables.keys():
        emit('message', "table does not exist")
    else:
        msg = escape_html(data['msg'])
        username = data['username']
        emit('message', f"{username}: {msg}", to=table_id)


def valid_username(username):
    for char in username:
        if char not in all_chars:
            return False
    if len(username) < 3 or len(username) > 20:
        return False
    return True


socket.run(app, allow_unsafe_werkzeug=True, debug=True)
