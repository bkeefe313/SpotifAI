import spotipy
from spotipy.oauth2 import SpotifyOAuth

"""
send a post request that looks like this:
curl -X POST "https://accounts.spotify.com/api/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=client_credentials&client_id=your-client-id&client_secret=your-client-secret"
"""

def login(client_id, client_secret):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                               client_secret=client_secret,
                                               redirect_uri="http://localhost:8888/callback",
                                               scope="user-library-read,user-library-modify,user-read-recently-played,user-read-currently-playing,user-modify-playback-state,user-read-playback-state,app-remote-control,playlist-read-private,playlist-modify-private,user-top-read,user-library-modify"))
    return sp