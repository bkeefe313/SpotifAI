# SpotifAI

### What it is
I see OpenAI and generative AI tools as interfacing mechanisms moreso than replacements for existing tools. This is not a music discovery, research, or playback tool. It IS an interface through which you can learn about your music and interact with it in a unique fashion.

### How to use it
You'll need a number of python packages -- spotipy, json, urllib, wikipediaapi, dotenv, openai, requests, annoy, flask, http, flash_socketio
And you'll need API keys for both Spotify and OpenAI. Keep in mind that assistant calls can get expensive, I would avoid using `gpt-4` since it racks up costs so fast. As it stands, this project uses `gpt-3.5-turbo-0125`
Once everything's set up, running main will ask you if you want to use the CLI interface (this is just for calling functions, not recommended until you read the code), or web interface (this will host a chat interface on your local machine to be interacted with in your browser).

The great thing about chatbots built with OpenAI or similar language models is that you don't really need directions on how to use it once the chat window is open -- have at it!

