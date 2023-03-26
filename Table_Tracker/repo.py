
import firebase_admin
from firebase_admin import credentials, firestore
cred = credentials.Certificate("config.json")
fb = firebase_admin.initialize_app(cred)
db = firestore.client()

def get_user_by_name(user_name: str) -> str:
    return db.collection('users').where('username', '==', user_name).get()
    
    
def add_user(username: str, pwd: str):
    db.collection('users').add({
            'username': username,
            'password': pwd
        })