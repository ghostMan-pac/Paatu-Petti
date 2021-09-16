# Paatu Petti
Paatu petti in malayalam means Music box. 


Modified Version of a [simple muisc bot by vbe0201](https://gist.github.com/vbe0201/ade9b80f2d3b64643d854938d40a0a2d) with added language and playlist support.




#### Features
1. Supports Playlists, this was a feature which was missed in the gist version
2. Multiple Languages, depending on the server owners preference, you can add and set you own language

## Installation
Install the follwing Dependencies
#### Dependencies
`python 3.5+`
`pip install -u discord youtube_dl pynacl`
add [FFMpeg](https://ffmpeg.org/download.html) to [enviornment path](https://www.wikihow.com/Install-FFmpeg-on-Windows)(step 12)

#### Adding bot in discord 
1. Create a discord bot account by going [here](https://discord.com/developers/applications) and logging in.
2. Add a new application.
3. Go under bot and click Add bot
    - The name that you set here will be seen by members in server 
    - description set is shown when you click the bot to check its profile
4. Now, go under OAuth2 and select the `bot` scope
5. select the permission you would like to give your bot
    - Required permissions:
        - Send Message
        - View Channels
        - Connct
        - Speak
        - Add Reactions
6. Copy the URL that is generated, It should look something like this:
    - `https://discord.com/api/oauth2/authorize?client_id=<clientID>&permissions=3148864&scope=bot`
7. The generated URL is the invite that you should give to people when you are adding the bot to a server.

#### Commands
prefix + command or aliases + args(optional) 

- `play[p] <link or name>`, Plays a song or a playlist from link
- `stop[s]`, Stops playing a song
- `skip`, Skips a song
- `pause`, pauses the playing song
- `resume`, resumes the song (if paused)
- `remove <no in queue>`, removes a song from the queue
- `lang <language>`, changes language
- `queue[q]`, shows the current queue
- `leave[dc, disconnect]`, disconnect from the voice channel
- `volume[v] <volume level>`, sets the volume of the bot to the specified level
- `now[current]`, shows the song which is being played 
- `summon/join`, joins the voice channel of the author who sent the command
- `shuffle`, shuffles the queue 
- `loop`, Loops the queue s 

## Contributing
#### Adding Language Support
To add language support(Everything inside Languages folder):
1. Make a copy of `en.json`
2. Rename it a 3 letter or 2 letter code of the language
3. Translate the contents of `en.json` into desired language
4. Append `"<language code>":["<acceptable !lang arguments for the language>"]` eg: `"en":["english","en","eng"]` into `languages.json`
