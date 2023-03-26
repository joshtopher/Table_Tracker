from flask import Flask

from flask_socketio import SocketIO



app = Flask(__name__, template_folder='../templates')
socket = SocketIO(app)

from Table_Tracker import views

socket.run(app, allow_unsafe_werkzeug=True, debug=True)
