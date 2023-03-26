from flask import request, render_template, redirect
from flask_socketio import  join_room, leave_room, emit
import random
import time
from Table_Tracker import app, socket, repo, rooms


ROOMS = rooms.RoomRegistry()


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
    user = repo.get_user_by_name(username)
    if user:
        return "Username Taken"
    else:
        repo.add_user(username, pwd)
        return redirect('/')


@app.post('/login')
def login():
    username = escape_html(request.form['username'])
    pwd = request.form['password']

    user = repo.get_user_by_name(username)
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
    if ROOMS.room_exists(table_id):
        return "table does not exist"
    else:
        response = redirect(f'/table/{table_id}')
        response.set_cookie('table_id', table_id)
        response.set_cookie('gm', 'false')
        return response


@app.get('/table/<table_id>')
def table(table_id):
    if ROOMS.room_exists(table_id):
        username = request.cookies.get('username')
        is_gm = request.cookies.get('gm')
        if username:
            ROOMS.add_user_to_room(table_id, username)
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
    username = request.cookies.get('username')
    if username:
        table_id = ROOMS.add_room()
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
    ROOMS.remove_user_from_room(table_id, username)
    time.sleep(1)
    if not ROOMS.user_in_room(table_id, username):
        emit('message', f"{username} left the table", to=table_id)
        leave_room(table_id)


@socket.event()
def gm_leave(data):
    table_id = data['table']
    username = data['username']
    if ROOMS.room_exists(table_id):
        ROOMS.remove_user_from_room(table_id, username)
    time.sleep(1)
    if not ROOMS.user_in_room(table_id, username):
        emit('message', f"table {table_id} is now closed", to=table_id)
        emit('close', to=table_id)
        leave_room(table_id)
        ROOMS.remove_room(table_id)


@socket.event()
def message(data):
    table_id = data['table']
    if ROOMS.room_extsts(table_id):
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


