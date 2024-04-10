import login
import dotenv
import spotifai
from openai import OpenAI
from http.server import HTTPServer 
from flask import Flask, request, render_template
from flask_socketio import SocketIO
import json
import requests
import wikipediaapi

app = Flask(__name__)
socketio = SocketIO(app)
client_id = dotenv.get_key('.env', 'CLIENT_ID')
client_secret = dotenv.get_key('.env', 'CLIENT_SECRET')
sp = login.login(client_id, client_secret)
sai = spotifai.Spotifai(sp)

def add(x, y):
    return x + y

def handle_message(msg):
    if msg == "exit":
        exit()
    responses = sai.handle_prompt(msg)    
    for response in responses:
        socketio.emit(response['type'], response['content'])

@app.route('/')
def session():
    return render_template('index.html')

def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')

@socketio.on('user-message')
def handle_my_custom_event(json_data, methods=['GET', 'POST']):
    print('received message: ' + str(json_data))
    socketio.emit('message-received', json_data, callback=messageReceived)
    handle_message(json_data['message'])
    

commands = {
    "current_track": sai.get_current_track,
    "find_track": sai.find_track,
    "find_album": sai.find_album,
    "find_artist": sai.find_artist,
    "find_recommendations": sai.find_recommendations,
    "research": sai.research,
    "queue_track": sai.queue_track,
    "play_track": sai.play_track,
    "get_track_uri": sai.get_track_uri,
    "get_album_uri": sai.get_album_uri,
    "get_oembed": spotifai.get_oembed,
    "add": add,
    "exit": exit,
    "download_library": sai.download_user_library,
    "get_similar": sai.get_similar
}
if __name__ == "__main__":
    choice = input("Web or CLI? (w/c): ")
    if choice == "w":
        print(sp.current_user())
        socketio.run(app)
    else:
        while True:
            cmd = input("Enter a command: ")
            if cmd == "exit":
                break
            elif cmd in commands:
                args = input("Enter arguments: ")
                result = "None"
                args = eval(args)
                result = commands[cmd](*args)
                print("running command " + str(commands[cmd]) + " with args " + str(args))
                print(result)
            else:
                print("Invalid command.")