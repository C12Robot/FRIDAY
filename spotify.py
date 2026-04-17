import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

SCOPE = "user-modify-playback-state user-read-playback-state user-read-currently-playing playlist-read-private"

def get_spotify():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=SCOPE,
        cache_path=os.path.join(os.path.dirname(__file__), ".spotify_cache")
    ))

def spotify_play(query):
    try:
        sp = get_spotify()
        devices = sp.devices()
        if not devices['devices']:
            return "No active Spotify device found. Open Spotify on your laptop first."
        
        device_id = devices['devices'][0]['id']
        results = sp.search(q=query, limit=1, type='track')
        tracks = results['tracks']['items']
        
        if not tracks:
            return f"Couldn't find '{query}' on Spotify."
        
        track = tracks[0]
        sp.start_playback(device_id=device_id, uris=[track['uri']])
        return f"Playing {track['name']} by {track['artists'][0]['name']}"
    except Exception as e:
        return f"Spotify error: {str(e)}"

def spotify_pause():
    try:
        sp = get_spotify()
        sp.pause_playback()
        return "Paused."
    except Exception as e:
        return f"Spotify error: {str(e)}"

def spotify_next():
    try:
        sp = get_spotify()
        sp.next_track()
        return "Skipped to next track."
    except Exception as e:
        return f"Spotify error: {str(e)}"

def spotify_current():
    try:
        sp = get_spotify()
        track = sp.current_playback()
        if not track or not track['is_playing']:
            return "Nothing is playing right now."
        name = track['item']['name']
        artist = track['item']['artists'][0]['name']
        return f"Currently playing: {name} by {artist}"
    except Exception as e:
        return f"Spotify error: {str(e)}"

def spotify_play_playlist(name):
    try:
        sp = get_spotify()
        devices = sp.devices()
        if not devices['devices']:
            return "No active Spotify device found. Open Spotify on your laptop first."
        
        device_id = devices['devices'][0]['id']
        playlists = sp.current_user_playlists()
        
        for playlist in playlists['items']:
            if name.lower() in playlist['name'].lower():
                sp.start_playback(device_id=device_id, context_uri=playlist['uri'])
                return f"Playing playlist: {playlist['name']}"
        
        return f"Couldn't find playlist '{name}'."
    except Exception as e:
        return f"Spotify error: {str(e)}"