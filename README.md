# Paatu Petti
Paatu petti in malayalam means Music box. 


Modified Version of a [simple muisc bot by vbe0201](https://gist.github.com/vbe0201/ade9b80f2d3b64643d854938d40a0a2d) with added language and playlist support.


### Dependencies
`python 3.5+`
`pip install -u discord youtube_dl`
add [FFMpeg](https://ffmpeg.org/download.html) to [enviornment path](https://www.wikihow.com/Install-FFmpeg-on-Windows)(step 12)


### Adding Language Support
To add language support(Everything inside Languages folder):
1. Make a copy of `en.json`
2. Rename it a 3 letter or 2 letter code of the language
3. Translate the contents of `en.json` into desired language
4. Append `"<language code>":["<acceptable !lang arguments for the language>"]` eg: `"en":["english","en","eng"]` into `languages.json`
