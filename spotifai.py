import spotipy
import json
from urllib.parse import quote
import wikipediaapi
import dotenv
from openai import OpenAI
import requests
import songdb
import os
import random

sys_msg = {"role": "system", "content": "You are SpoitfAI, a helpful Spotify assistant. You can be asked to recommend music, share thoughts on it, play it for the user, and more."}
feature_meanings={
    'acousticness': 'A confidence measure from 0.0 to 1.0 of whether the track is acoustic. 1.0 represents high confidence the track is acoustic.',
    'analysis_url': 'A URL to access the full audio analysis of this track. An access token is required to access this data.',
    'danceability': 'Danceability describes how suitable a track is for dancing based on a combination of musical elements including tempo, rhythm stability, beat strength, and overall regularity. A value of 0.0 is least danceable and 1.0 is most danceable.',
    'duration': 'The duration of the track in milliseconds.',
    'energy': 'Energy is a measure from 0.0 to 1.0 and represents a perceptual measure of intensity and activity. Typically, energetic tracks feel fast, loud, and noisy. For example, death metal has high energy, while a Bach prelude scores low on the scale. Perceptual features contributing to this attribute include dynamic range, perceived loudness, timbre, onset rate, and general entropy.',
    'id': 'The Spotify ID for the track.',
    'instrumentalness': 'Predicts whether a track contains no vocals. "Ooh" and "aah" sounds are treated as instrumental in this context. Rap or spoken word tracks are clearly "vocal". The closer the instrumentalness value is to 1.0, the greater likelihood the track contains no vocal content. Values above 0.5 are intended to represent instrumental tracks, but confidence is higher as the value approaches 1.0.',
    'key': 'The key the track is in. Integers map to pitches using standard Pitch Class notation. E.g. 0 = C, 1 = C♯/D♭, 2 = D, and so on. If no key was detected, the value is -1.',
    'liveness': 'Detects the presence of an audience in the recording. Higher liveness values represent an increased probability that the track was performed live. A value above 0.8 provides strong likelihood that the track is live.',
    'loudness': 'The overall loudness of a track in decibels (dB). Loudness values are averaged across the entire track and are useful for comparing relative loudness of tracks. Loudness is the quality of a sound that is the primary psychological correlate of physical strength (amplitude). Values typically range between -60 and 0 db.',
    'mode': 'Mode indicates the modality (major or minor) of a track, the type of scale from which its melodic content is derived. Major is represented by 1 and minor is 0.',
    'speechiness': 'Speechiness detects the presence of spoken words in a track. The more exclusively speech-like the recording (e.g. talk show, audio book, poetry), the closer to 1.0 the attribute value. Values above 0.66 describe tracks that are probably made entirely of spoken words. Values between 0.33 and 0.66 describe tracks that may contain both music and speech, either in sections or layered, including such cases as rap music. Values below 0.33 most likely represent music and other non-speech-like tracks.',
    'tempo': 'The overall estimated tempo of a track in beats per minute (BPM). In musical terminology, tempo is the speed or pace of a given piece and derives directly from the average beat duration.',
    'time_signature': 'An estimated time signature. The time signature (meter) is a notational convention to specify how many beats are in each bar (or measure). The time signature ranges from 3 to 7 indicating time signatures of "3/4", to "7/4".',
    'track_href': 'A link to the Web API endpoint providing full details of the track.',
    'type': 'NA. The object type.',
    'uri': 'The Spotify URI for the track',
    'valence': 'A measure from 0.0 to 1.0 describing the musical positiveness conveyed by a track. Tracks with high valence sound more positive (e.g. happy, cheerful, euphoric), while tracks with low valence sound more negative (e.g. sad, depressed, angry).'
}
wiki = wikipediaapi.Wikipedia('Spotifai (bkeefe313@gmail.com)','en')
messages = []

# Load the tools we'll use for the assistant
with open('tools.json') as f:
    tools = json.load(f)

"""Gets a spotify embed in html. Good for looking pretty."""
def get_oembed(item):
    encoded_url = quote(item.url, safe='')
    url = f"https://open.spotify.com/oembed?url={encoded_url}"
    resp = requests.get(url).json()
    return resp['html']

"""A session of the app. Basically interfaces openai and spotipy."""
class Spotifai:
    def __init__ (self, sp):
        self.sp:spotipy.Spotify = sp
        self.client = OpenAI(api_key=dotenv.get_key('.env', 'OPENAI_API_KEY'))
        self.assistant = self.client.beta.assistants.create(
            name="SpotifAI",
            description="A helpful Spotify assistant.",
            tools=tools,
            instructions="You are SpotifAI, a helpful Spotify assistant. You can be asked to recommend music, share thoughts on it, play it for the user, and more.",
            model="gpt-3.5-turbo-0125"
        )
        self.db = None
        if os.path.exists("data/songdb.ann"):
            self.load_song_db()
            with open("data/sp_to_db_id.json") as f:
                self.sp_to_db_id = json.load(f)
            with open("data/db_to_sp_id.json") as f:
                self.db_to_sp_id = json.load(f)
        self.tool_names = {
            "get_current_track": self.get_current_track_TOOL,
            "find_track": self.find_track_TOOL,
            "find_album": self.find_album_TOOL,
            "find_artist": self.find_artist_TOOL,
            "find_recommendations": self.find_recommendations_TOOL,
            "research": self.research_TOOL,
            "queue_track": self.queue_track_TOOL,
            "play_track": self.play_track_TOOL,
            "get_track_uri": self.get_track_uri_TOOL,
            "get_album_uri": self.get_album_uri_TOOL,
            "get_similar": self.get_similar_TOOL,
            "basic_prompt": self.basic_prompt_TOOL,
            "secondary_research": self.secondary_research_TOOL,
            "scour_page": self.scour_page_TOOL,
            "describe_track_features": self.get_track_features_TOOL
        }
    
    """Download up to 5000 of the user's saved library tracks. Store the data both in songdb (vectorized) and in json files for reference."""
    def download_user_library(self):
        self.db = songdb.SongDB(13)
        print("Downloading user library...")
        tracks = []
        self.sp_to_db_id = {}
        self.db_to_sp_id = {}
        for i in range(0, 5000, 50):
            results = self.sp.current_user_saved_tracks(limit=50, offset=i)
            iter = 0
            if len(results['items']) == 0:
                break
            for item in results['items']:
                # set up the track
                track = Track(item['track'], db_id=iter+i)
                # store the track in the reference maps
                self.sp_to_db_id[track.id] = iter+i
                self.db_to_sp_id[iter+i] = track.id
                print("found " + track.name)
                tracks.append(track)
                iter += 1
        for i in range(0, len(tracks), 100):
            if len(tracks) - i < 100:
                working_tracks = [track for track in tracks[i:]]
            else:
                working_tracks = [track for track in tracks[i:i+100]]
            features = self.sp.audio_features([track.id for track in working_tracks])
            for j in range(0, len(working_tracks)):
                working_tracks[j].set_features(features[j])
        
        for track in tracks:
            if track.features is not None:
                self.db.add_track(track)
            
        self.db.build()
        self.db.save("data/songdb.ann")

        with open("data/user_library.json", "w") as f:
            data = [track.__dict__ for track in tracks]
            json.dump(data, f)

        with open("data/sp_to_db_id.json", "w") as f:
            json.dump(self.sp_to_db_id, f)
        with open("data/db_to_sp_id.json", "w") as f:
            json.dump(self.db_to_sp_id, f)
    
    """Get the user library db if it already exists"""
    def load_song_db(self):
        try:
            self.db = songdb.SongDB.load("data/songdb.ann", 13)
        except:
            print("Failed to fetch songdb.")
            self.db = None


    """Below are the methods that the assistant has available as tools. There is a corresponding 'TOOL' version of each method that helps generalize interfacing with the assistant."""


    """Get the currently playing track."""
    def get_current_track(self):
        current_track = self.sp.current_playback()
        if current_track is None:
            return None
        track = current_track['item']
        return Track(track)
    
    def get_current_track_TOOL(self, args, responses):
        output = self.get_current_track()
        if output is None:
            responses.append({"type": "message", "content": "You are not currently playing anything."})
            return "None"
        responses.append({"type": "message", "content": "Currently playing " + output.chat_string() + "."})
        return json.dumps(output.__dict__)
    
    """Play a track on the user's Spotify."""
    def play_track(self, uri):
        if 'artist' in uri:
            track = self.sp.artist_top_tracks(uri)['tracks'][0]
            uri = track['uri']
        if 'album' in uri:
            track = self.sp.album_tracks(uri)['items'][random.randint(0, len(self.sp.album_tracks(uri)['items'])-1)]
            uri = track['uri']
        if self.sp.current_playback() is None:
            self.sp.start_playback(uris=[uri])
        else:
            # I prefer to queue the track and then play it, less interruptive
            self.sp.add_to_queue(uri)
            self.sp.next_track()
        return uri
    
    def play_track_TOOL(self, args, responses):
        real_uri = self.play_track(args['track'])
        responses.append({"type": "message", "content": "Playing " + self.sp.track(real_uri)['name'] + "."})
        return "Playing " + args['track'] + "."
    

    """Place a track in the user's Spotify queue."""
    def queue_track(self, uri):
        if 'artist' in uri:
            track = self.sp.artist_top_tracks(uri)['tracks'][0]
            uri = track['uri']
        if 'album' in uri:
            track = self.sp.album_tracks(uri)['items'][random.randint(0, len(self.sp.album_tracks(uri)['items']))]
            uri = track['uri']
        self.sp.add_to_queue(uri)
        return uri
    
    def queue_track_TOOL(self, args, responses):
        real_uri = self.queue_track(args['track'])
        responses.append({"type": "message", "content": "Queued " + self.sp.track(real_uri) + "."})
        return "Queued " + args['track'] + "."
    

    """Get tracks with similar features to a given track, using the songdb vector data for library tracks. Does not work with tracks not in the user's library."""
    def get_similar(self, track_id):
        # make sure to trim off the "spotify:track:" part if it's there
        if "spotify:track:" in track_id:
            track_id = track_id.split(":")[2]
        try:
            track_db_id = self.sp_to_db_id[track_id]
        except KeyError:
            return None
        similar = self.db.get_similar(track_db_id)
        tracks = [self.sp.track(self.db_to_sp_id[str(db_id)]) for db_id in similar]
        return [Track(track) for track in tracks]

    def get_similar_TOOL(self, args, responses):
        output = self.get_similar(args['id'])
        if output is None:
            responses.append({"type": "message", "content": "I couldn't find any similar tracks."})
            return "None"
        responses.append({"type": "message", "content": "Here are some similar tracks."})
        for track in output:
            responses.append({"type": "embed", "content": get_oembed(track)})
        return json.dumps([track.__dict__ for track in output])
    
    """Returns a list of features for a given track"""
    def get_track_features(self, query_track):
        if type(query_track) is not Track:
            track = self.find_track(query_track)
        else:
            track = query_track
        if track.features == None:
            track.set_features(self.sp.audio_features([track.uri]))
        return track.features
    
    def get_track_features_TOOL(self, args, responses):
        output = self.get_track_features(args['track'])
        feature_meanings_msg = {"role":"system","content":f'The following are the descriptions of the meanings of features of a track you are to describe: {json.dumps(feature_meanings)}'}
        description = self.basic_prompt([sys_msg, feature_meanings_msg, {"role":"user","content":f'Give a general linguistic (avoid numbers) description of the song with the following features: {json.dumps(output)}'}]).content
        responses.append({"type":"message","content":"From the information I have, this track could be described as: <br>" + description})
        return json.dumps(output)
    

    """Have the model generate a response to a prompt, using ChatCompletions rather than assistant API calls."""
    def basic_prompt(self, prompt):
        completion = self.client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=prompt,
        )
        return completion.choices[0].message
    
    def basic_prompt_TOOL(self, args, responses):
        output = self.basic_prompt([sys_msg,{"role": "user", "content": args['prompt']}]).content
        responses.append({"type": "message", "content": output})
        return output
    

    """Find a track on Spotify by searching with a query, or using a uri. Returns the top result."""
    def find_track(self, query):
        try:
            track = self.sp.track(track_id=query)
        except:
            results = self.sp.search(q=query, limit=1)
            if results['tracks']['total'] == 0:
                return None
            track = results['tracks']['items'][0]
        return Track(track)
    
    def find_track_TOOL(self, args, responses):
        output = self.find_track(args['query'])
        if output is None:
            responses.append({"type": "message", "content": "I couldn't find any tracks matching that query."})
            return "None"
        responses.append({"type": "message", "content": "Here's a track called " + output.chat_string() + "."})
        responses.append({"type": "embed", "content": get_oembed(output)})
        return json.dumps(output.__dict__)


    """Find an album on Spotify by searching with a query. Returns the top result."""
    def find_album(self, query):
        results = self.sp.search(q=query, limit=1, type='album')
        if results['albums']['total'] == 0:
            return None
        album = results['albums']['items'][0]
        return Album(album)
    
    def find_album_TOOL(self, args, responses):
        output = self.find_album(args['query'])
        if output is None:
            responses.append({"type": "message", "content": "I couldn't find any albums matching that query."})
            return "None"
        responses.append({"type": "message", "content": "Here's an album called " + output.chat_string() + "."})
        responses.append({"type": "embed", "content": get_oembed(output)})
        return json.dumps(output.__dict__)
    
    
    """Find an artist on Spotify by searching with a query. Returns the top result."""
    def find_artist(self, query):
        results = self.sp.search(q=query, limit=1, type='artist')
        if results['artists']['total'] == 0:
            return None
        artist = results['artists']['items'][0]
        return Artist(artist)
    
    def find_artist_TOOL(self, args, responses):
        output = self.find_artist(args['query'])
        if output is None:
            responses.append({"type": "message", "content": "I couldn't find any artists matching that query."})
            return "None"
        responses.append({"type": "message", "content": "Here's an artist called " + output.name + "."})
        return json.dumps(output.__dict__)
    
    
    """Get a list of Spotify's recommendations based on up to 5 total seed tracks, artists, and/or genres. Returns up to 5 recommendations."""
    def find_recommendations(self, seed_tracks, seed_artists, seed_genres, seed_albums):
        for album in seed_albums:
            if len(seed_artists) >= 5:
                break
            seed_artists.append(self.sp.album(album)['artists'][0].id)
        results = self.sp.recommendations(seed_tracks=seed_tracks, seed_artists=seed_artists, seed_genres=seed_genres)
        return results
    
    def find_recommendations_TOOL(self, args, responses):
        try:
            seed_tracks = args['seed_tracks']
        except KeyError:
            seed_tracks = []
        try:
            seed_artists = args['seed_artists']
        except KeyError:
            seed_artists = []
        try:
            seed_genres = args['seed_genres']
        except KeyError:
            seed_genres = []
        if len(seed_tracks) + len(seed_artists) + len(seed_genres) == 0:
            return "None"
        if len(seed_tracks) + len(seed_artists) + len(seed_genres) > 5:
            return "Too many seeds. Please limit to 5."
        output = self.find_recommendations(seed_tracks, seed_artists, seed_genres, seed_genres)
        responses.append({"type": "message", "content": "Here are some recommendations."})
        for i in range(0, min(len(output['tracks']), 5)):
            tr = Track(output['tracks'][i])
            responses.append({"type": "embed", "content": get_oembed(tr)})
        return json.dumps(output)
    
    
    """Have the model research an album, track, or artist on Wikipedia."""
    def research(self, type, subject, query=""):
        name = subject.replace(" ", "_")
        print(name)
        if type == "artist":
            result = ""
            # oftentimes Wikipedia pages for artists are under the name of the artist followed by "(musician)" or "(band)"
            # try these first to avoid disambiguation pages
            name = subject + "_(band)"
            page = wiki.page(name)
            if not page.exists():
                name = subject + "_(musician)"
                page = wiki.page(name)
            if not page.exists():
                name = subject
                page = wiki.page(name)
            if page.exists():
                result = self.summarize_wiki(page, type, query)
            else:
                result = "I couldn't find any information about that artist."
        if type == "track":
            name = subject + "_(song)"
            page:wikipediaapi.WikipediaPage = wiki.page(name)
            if page.exists():
                result = self.summarize_wiki(page, type, query)
            else:
                result = "I couldn't find info on this track, but here's what I found about the artist:" + self.research("artist", self.find_track(subject).artist['name'], query)
        if type == "album":
            page = wiki.page(subject + "_(album)")
            if not page.exists():
                page = wiki.page(subject)
            if page.exists():
                result = self.summarize_wiki(page, type, query)
            else:
                result = "I couldn't find info on this album, but here's what I found about the artist:" + self.research("album", self.find_artist(subject).name, query)
        return result
    
    def research_TOOL(self, args, responses):
        try:
            query = args['query']
        except KeyError:
            query = ""
        output = self.research(args['type'], args['object'], query)
        responses.append({"type": "message", "content": output})
        return output
    

    """Search for things on Wikipedia besides artists, albums, or tracks."""
    def secondary_research(self, subject, query=""):
        page = wiki.page(subject)
        if page.exists():
            result = self.summarize_wiki(page, "general subject", query)
        else:
            result = "No info found."
        return result
    
    def secondary_research_TOOL(self, args, responses):
        try:
            query = args['query']
        except KeyError:
            query = ""
        output = self.secondary_research(args['subject'], query)
        responses.append({"type": "message", "content": output})
        return output
    

    """'Scour' a Wikipedia page for links to articles that contain a query and are relevant to a type."""
    def scour_page(self, page_name, query, type):
        page = wiki.page(page_name)
        if not page.exists():
            return []
        potential_links = []
        for link in page.links:
            p = wiki.page(link)
            # only consider links that contain the query and are relevant to the type
            if query in p.summary and type in p.summary:
                potential_links.append(p)
        return potential_links
    
    def scour_page_TOOL(self, args, responses):
        output = self.scour_page(args['page_name'], args['query'], args['type'])
        if len(output) == 0:
            responses.append({"type": "message", "content": "I couldn't find any relevant links."})
            return "None"
        responses.append({"type": "message", "content": "Here are some relevant links."})
        for page in output:
            responses.append({"type": "message", "content": f'<a target="_blank" href={page.fullurl}>{page.title}</a>'})

        final_output = [page.title + ":" + page.summary for page in output]
        return json.dumps(final_output)
    
    """Get the URI (spotify identifier) of a track."""
    def get_track_uri(self, track):
        return track.uri
    
    def get_track_uri_TOOL(self, args, responses):
        output = self.get_track_uri(args['track'])
        return output
    

    """Get the URI (spotify identifier) of an album."""
    def get_album_uri(self, album):
        return album.uri
    
    def get_album_uri_TOOL(self, args, responses):
        output = self.get_album_uri(args['album'])
        return output
    

    """The rest are internal functions that the assistant doesn't have direct access to."""

    """Summarizes a Wikipedia page by asking the LLM to do so (chat completion, not assistant)."""
    def summarize_wiki(self, page:wikipediaapi.WikipediaPage, type, query):
        print(page.title)
        # if the user has a specific query, find relevant info. Otherwise, summarize the page.
        if(query != ""):
            research_msg = {"role": "system", "content": f"Here is information from Wikipedia about the {type} {page.title}: {page.text}"}
            result = self.basic_prompt([sys_msg,research_msg,{"role": "user", "content": query}]).content
            result += "<br>" + f'Information obtained from <a target=”_blank” href="{page.fullurl}">'+ page.fullurl +"</a>. Note that this model can hallucinate information."
        else:
            result = self.basic_prompt([sys_msg,{"role": "system", "content": "Summarize the following content. CONTENT:" + page.text}]).content
            result +="<br>" + f'Information obtained from <a target=”_blank” href="{page.fullurl}">' + page.fullurl + "</a>"
        return result
    

    """Tries to have the model to test the relevance of the information it's found """
    def ensure_relevance(self, info, query):
        relevance_msg = {"role": "system", "content": f"Here is the information found: {info}. Is this relevant to the query? Query: {query}. Just say yes or no."}
        response = self.basic_prompt([sys_msg,relevance_msg]).content
        print("Relevant? " + response)
        return response.lower() == "yes"

    
    """Handle a user prompt. Given a message, will feed the request to the assistant and complete the assistant's designated tasks."""
    # TODO Refactor this function, it's messy
    def handle_prompt(self, msg):
        responses = []
        addendum = ""
        messages.append({"role": "user", "content": msg})
        # setup thread and run
        thread = self.client.beta.threads.create(
            messages=messages,
        )
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant.id,
            tools=tools
        )
        # wait until run finishes
        while run.status != "expired" and run.status != "completed" and run.status != "failed" and run.status != "cancelled":
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            run_steps = self.client.beta.threads.runs.steps.list(
                thread_id=thread.id,
                run_id=run.id
            )
            # print the step details, for debugging
            if len(run_steps.data) > 0:
                run_step = self.client.beta.threads.runs.steps.retrieve(
                    thread_id=thread.id,
                    run_id=run.id,
                    step_id=run_steps.data[0].id
                )
                print(run_step.step_details)
            # handle run actions
            if run.status == "requires_action":
                outputs = []
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    # tell user what's happening :D
                    responses.append({"type": "system", "content": "Running tool: " + tool_call.function.name + " with args " + tool_call.function.arguments + "."})
                    print(tool_call.function.name)
                    # get the function and run it
                    func = self.tool_names[tool_call.function.name]
                    args = json.loads(tool_call.function.arguments)
                    output = func(args, responses)
                    # keep track of the outputs for assistant
                    outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": output,
                            })
                # submit the outputs
                run = self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread.id,
                    run_id=run.id,
                    tool_outputs=outputs
                )
        # if we didn't do anything?
        if len(responses) == 0:
            response = self.basic_prompt([sys_msg,{"role": "user", "content": msg}]).content 
            responses.append({"type": "message", "content": response})

        return responses

"""Container for track info"""
class Track:
    def __init__ (self, data, db_id=None):
        self.name = data['name']
        self.id = data['id']
        self.uri = data['uri']
        self.url = data['external_urls']['spotify']
        self.db_id = db_id
        self.features = None
        self.artist = {"name": data['artists'][0]['name'], "uri": data['artists'][0]['uri']}
        self.album = {"name": data['album']['name'], "uri": data['album']['uri']}

    def __str__(self):
        return f"{self.name} by {self.artist['name']} from {self.album['name']} ({self.uri})"
    
    def chat_string(self):
        return f"{self.name} by {self.artist['name']} from {self.album['name']}"
    
    def set_features(self, features):
        self.features = features

"""Container for album info"""
class Album:
    def __init__ (self, album):
        self.name = album['name']
        self.uri = album['uri']
        self.url = album['external_urls']['spotify']
        self.year = album['release_date']
        self.artist = {"name": album['artists'][0]['name'], "uri": album['artists'][0]['uri']}

    def __str__(self):
        return f"{self.name} by {self.artist['name']} ({self.uri})"
    
    def chat_string(self):
        return f"{self.name} by {self.artist['name']}"
    
"""Container for artist info"""
class Artist:
    def __init__ (self, artist):
        self.name = artist['name']
        self.uri = artist['uri']
        self.url = artist['external_urls']['spotify']
        self.genres = artist['genres']
        self.popularity = artist['popularity']
        self.images = artist['images']

    def __str__(self):
        return f"{self.name} ({self.uri})"
    
    def chat_string(self):
        return f"{self.name}"