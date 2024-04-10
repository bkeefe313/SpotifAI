# SpotifAI

### What it is
I see OpenAI and generative AI tools as interfacing mechanisms moreso than replacements for existing tools. This is not a music discovery, research, or playback tool. It IS an interface through which you can learn about your music and interact with it in a unique fashion.

### How to use it
You'll need a number of python packages -- `spotipy`, `json`, `urllib`, `wikipediaapi`, `dotenv`, `openai`, `requests`, `annoy`, `flask`, `http`, `flash_socketio`
And you'll need API keys for both Spotify and OpenAI. Keep in mind that assistant calls can get expensive, I would avoid using `gpt-4` since it racks up costs so fast. As it stands, this project uses `gpt-3.5-turbo-0125`
Once everything's set up, running main will ask you if you want to use the CLI interface (this is just for calling functions, not recommended until you read the code), or web interface (this will host a chat interface on your local machine to be interacted with in your browser).

The great thing about chatbots built with OpenAI or similar language models is that you don't really need directions on how to use it once the chat window is open -- have at it!

### Capabilities
This app is built on the OpenAI Assistants API, and the assistant is given access to a number of Spotify-related functions, as well as Wikipedia, and some internal tools. The Spotify functions (for example, `find_track`, `play_track`, `find_album`, or `get_track_features`) make Spotify API calls, allowing the assistant to see what the user is listening to, get recommendations from spotify, find and play other songs, etc. The Wikipedia API interfacing allows the assistant to do research on a particular topic, typically an artist, song, or album, and garner some amount of information about the music from there. The idea is to potentially cross reference between information on Wikipedia and real, listenable music on Spotify, such that the user can discover related music or interesting musical information by learning about what they already know through a simple interface.
