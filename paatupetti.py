import json
import asyncio
import functools
import itertools
import math
import random
import discord
import validators
import youtube_dl
from async_timeout import timeout
from discord.ext import commands

youtube_dl.utils.bug_reports_message = lambda: ''

langSupport = {}


def loadLang(lang: str):
    with open("./languages/" + lang + ".json", 'r', encoding='utf-8') as langRead:
        global langSupport
        langSupport.clear()
        langSupport = json.load(langRead)
        print(langSupport["langChangeMessage"])


def r(): return random.randint(0, 255)


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'yesplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: commands.Context, search=None, url=None, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()
        song_url = ""
        info = ""
        partial = functools.partial(
            cls.ytdl.extract_info, search or url, download=False)
        data = await loop.run_in_executor(None, partial)
        if search:
            song_url, info = data['entries'][0]['url'], data['entries'][0]
        elif url:
            song_url, info = data['url'], data
        
        return cls(ctx, discord.FFmpegPCMAudio(song_url, **cls.FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        durationMessage = langSupport["durationMessage"]
        if days > 0:
            duration.append('{} {}'.format(days, durationMessage[0]))
        if hours > 0:
            duration.append('{} {}'.format(hours, durationMessage[1]))
        if minutes > 0:
            duration.append('{} {}'.format(minutes, durationMessage[2]))
        if seconds > 0:
            duration.append('{} {}'.format(seconds, durationMessage[3]))

        return ', '.join(duration)

class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embedMessage = langSupport["embedStrings"]
        embed = (discord.Embed(title=embedMessage[0],
                               description='[{0.source.title}]({0.source.url})'.format(
                                   self),
                               color=discord.Colour.from_rgb(r(), r(), r()))
                 .add_field(name=embedMessage[1], value=self.source.duration)
                 .add_field(name=embedMessage[2], value=self.requester.mention)
                 .add_field(name=embedMessage[3], value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

        self._loadLang()

    def _loadLang(self):
        langRead = open("./languages/serverLang.json", "r")
        jsonData = json.load(langRead)
        langRead.close()
        if not (str(self._ctx.guild.id) in jsonData):
            langRead = open("./languages/serverLang.json", "w")
            jsonData.update({str(self._ctx.guild.id): 'en'})
            langRead.truncate()
            json.dump(jsonData, langRead)
            langRead.close()
        loadLang(jsonData[str(self._ctx.guild.id)])

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.loop:
                # Try to get the next song within 3 minutes.
                # If no song will be added to the queue in time,
                # the player will disconnect due to performance
                # reasons.
                try:
                    async with timeout(180):  # 3 minutes
                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return

            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            message:discord.message = await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()
            
            await message.delete()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage()

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send(langSupport["defaultError"] + '{}'.format(str(error)))

    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='summon', aliases=['vaada', 'vaa'])
    @commands.has_permissions(manage_guild=True)
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.

        If no channel was specified, it joins your channel.
        """

        if not channel and not ctx.author.voice:
            raise VoiceError(
                'You are neither connected to a voice channel nor specified a channel to join.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='leave', aliases=['disconnect', 'fuckoff', 'poda', 'pomyre', 'omkv', 'dc'])
    @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            return await ctx.send(langSupport["voiceChannelError"])

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='volume', aliases=['shabhdam','v'])
    async def _volume(self, ctx: commands.Context, *, volume: int):
        """Sets the volume of the player."""

        if not ctx.voice_state.is_playing:
            return await ctx.send(langSupport["noSongError"])

        if 0 > volume > 100:
            return await ctx.send(langSupport["volumeError"])

        ctx.voice_state.volume = volume / 100
        await ctx.send(langSupport["volumeSetMessage"].format(volume))

    @commands.command(name='now', aliases=['current', 'playing'])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""

        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.command(name='pause', aliases=['wait'])
    @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='resume', aliases=['padiko'])
    @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if not ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    @commands.command(name='stop', aliases=['nirth'])
    @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()

        if not ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @commands.command(name='skip', aliases=['maatu'])
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send(langSupport["noSongError"])

        await ctx.message.add_reaction('⏭')
        ctx.voice_state.skip()

    @commands.command(name='queue', aliases=['q'])
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """Shows the player's queue.

        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send(langSupport["noQueueError"])

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(
                i + 1, song)
        message = langSupport['tracks']
        pageLang = langSupport['page']
        embed = (discord.Embed(description='**{} {}:**\n\n{}'.format(len(ctx.voice_state.songs), message, queue))
                 .set_footer(text='{} {}/{}'.format(pageLang, page, pages)))
        await ctx.send(embed=embed)

    @commands.command(name='shuffle', aliases=['mix'])
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send(langSupport["noQueueError"])

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')

    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send(langSupport["noQueueError"])

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    # @commands.command(name = 'seek')
    # async def _seek(self, ctx: commands.Context, time:str):

    @commands.command(name='loop', aliases=['l'])
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song.

        Invoke this command again to unloop the song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send(langSupport["noSongError"])

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction('✅')

    @commands.command(name='play', aliases=["paadu", "p"])
    async def _play(self, ctx: commands.Context, *, search: str):
        """Plays a song.

        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        """

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            if validators.url(search):
                videoData = YTDLSource.ytdl.extract_info(
                    search, download=False)
                if 'entries' in videoData:
                    for i, item in enumerate(videoData['entries']):
                        await self.trySourceAdd(ctx, url=item['webpage_url'], queue = True)
                        if i == len(videoData['entries']) - 1:
                            await ctx.send(langSupport["playlistQueueAdd"].format(i+1))
                else:
                    await self.trySourceAdd(ctx, url=search)
            else:
                await self.trySourceAdd(ctx, search=search)

    async def trySourceAdd(self, ctx: commands.Context, search=None, url=None, queue=None):
        try:
            if search:
                source = await YTDLSource.create_source(ctx, search=search, loop=self.bot.loop)
            elif url:
                source = await YTDLSource.create_source(ctx, url=url, loop=self.bot.loop)

        except YTDLError as e:
            await ctx.send(langSupport["requestError"] + '{}'.format(str(e)))
        else:
            song = Song(source)

            await ctx.voice_state.songs.put(song)
            if not queue:
                await ctx.send(langSupport["addedToQueue"]+'{}'.format(str(source)))

    @commands.command(name='lang')
    async def _lang(self, ctx: commands.context, lang: str):
        """you can change the language of bot"""
        langData = {}
        with open("./languages/languages.json", "r") as langFile:
            langData = json.load(langFile)
        for key in langData.keys():
            if lang in langData[key]:
                loadLang(key)
                await ctx.send(langSupport["langChangeMessage"])
                with open("./languages/serverLang.json", "r") as langRead:
                    jsonData = json.load(langRead)
                if str(ctx.guild.id) in jsonData:
                    jsonData.update({str(ctx.guild.id): key})
                    langRead = open("./languages/serverLang.json", "w")
                    json.dump(jsonData, langRead)
                    langRead.close()
                return
        if not langSupport:
            ctx.send('Unable to find the language you specified')

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError(langSupport["channelJoinError"])

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError(langSupport["alreadyInVoiceError"])

bot = commands.Bot('.', description='വെറും ഒരു പാട്ടുപെട്ടി')
bot.add_cog(Music(bot))


@bot.event
async def on_ready():
    print('ready!')

bot.run('<token>')
