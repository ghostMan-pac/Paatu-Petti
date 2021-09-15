import json
import asyncio
import discord
import itertools
import random
import youtube_dl
import functools
from discord.ext import commands
from async_timeout import timeout

r = lambda: random.randint(0,255)

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
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    }

    FFMPEG_OPTIONS = {
        'options': '-vn'
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 1.0):
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
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))

        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{} days'.format(days))
        if hours > 0:
            duration.append('{} hours'.format(hours))
        if minutes > 0:
            duration.append('{} minutes'.format(minutes))
        if seconds > 0:
            duration.append('{} seconds'.format(seconds))

        return ', '.join(duration)


class queue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        ''' return the length of the queue '''
        return self.qsize()

    def clear(self):
        ''' Clear the queue '''
        self._queue.clear()

    def shuffle(self):
        ''' Shuffle the queue '''
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]

class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Ippol Padunna Paatu',
                               description='```css\n{0.source.title}\n```'.format(self),
                               color='#{}{}{}'.format(r(), r(), r()))
                 .add_field(name='Duration', value=self.source.duration)
                 .add_field(name='Requested by', value=self.requester.mention)
                 .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed
    
class musicState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context) -> None:
        '''
            Defines the music state of the bot
        '''
        self.bot = bot 
        self._ctx = ctx
        self.current = None         #current song
        self.voice = None           #voice channel
        self.next = asyncio.Event() #next song
        self.queue = queue()        #queue
        self.loop = False           #is looping or not
        self.exists = True
        
        self.audio_player = bot.loop.create_task(self.audio_player_task())
    def currentState(self, ctx): 
        ''' return the current state of bot'''
        if not self.current:
           return None
    
    async def stop(self):
        '''clear queue and disconnect'''
        self.queue.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None

    def is_playing(self):
        '''return if the bot is currently playing something'''
        return True if not self.current else False
    
    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()
        
    async def audio_player_task(self):
        '''Event loop'''
        while True:
            self.next.clear()
            if not self.loop:
                try:
                    async with timeout(180):
                        self.current = await self.queue.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    self.exists = False
                    return
                
            self.current.source.volume = self._volume
            self.voice.play(self.current.source, after=self.play_next_song)
            await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

class paatuPetti(commands.Cog):
    '''
    Main bot class
    '''    
    def __init__(self, bot: commands.Bot) -> None:
        '''initialize the bot with default state'''
        self.bot = bot
        self.voice_states = {}
        super().__init__()

    def get_voice_state(self, ctx:commands.Context):
        '''
        returns the current state of the voice the bot is in,
        in a specific discord guild/server (ie in voice or not)
        '''
        state = self.voice_states.get(ctx.guild.id)
        if not state or not state.exists:
            state = musicState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state            
        
        return state
    
    async def cog_before_invoke(self, ctx):
        '''what to do before bot init's on server side'''
        ctx.voice_state = self.get_voice_state(ctx)
    
    def cog_unload(self):
        '''when bot goes offline, clear all the queue and set states to none'''
        for state in self.voice_states.values():
            self.bot.loop.create_test(state.stop())
            
    @commands.command(name = "join", aliases = ['vaada', 'vaa'])
    async def join(self, ctx: commands.Context, channel: discord.VoiceChannel = None):
        '''Joins a voice channel(if specified) or joins the author's channel'''
        if not channel and not ctx.author.voice:
            await ctx.send("Nee eeth channelila?")
        
        dest = ctx.author.voice.channel or channel
        
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(dest)
            return
        
        ctx.voice_state.voice = await dest.connect()
                
    @commands.command(name = "play", aliases=['p', 'paadu'],pass_context = True)
    async def play(self, ctx: commands.Context, * , search:str):
        '''
        joins the voice channel(if not already joined) then playes
        a song from link or text.
        '''
        if not ctx.voice_state.voice:
            await ctx.invoke(self.join)

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                song = Song(source)

                await ctx.voice_state.queue.put(song)
                await ctx.send('Enqueued {}'.format(str(source)))                    
                                
                
    @play.before_invoke
    @join.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        '''
            Ensures if author in voice channel or in another channel
        '''
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send('Poyi Voice channel join cheyada')
        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                await ctx.send('njan paatu padi kond irikua')

    @commands.command(name = "stop")
    async def stop(self,ctx: commands.Context):
        '''
            Stops the current song, clears queue
        '''
        ctx.voice_state.songs.clear()

        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')
            
    @commands.command(name = "leave", aliases=['poda', 'omkv', 's', 'pomyre'])
    async def leave(self, ctx: commands.Context):
        '''
            Leave the voice chat and remove everthing in queue stops playing
        '''
        if not ctx.voice_state.voice:
            await ctx.send("Njan athin voice channelil illalo!")
        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]            

def main():
    token = str
    with open("config.json") as config:
        temp = json.load(config)
        bot = commands.Bot(command_prefix = temp["prefix"], description= "വെറും ഒരു പാട്ടുപെട്ടി")
        token = temp["discord_token"]
    
    bot.add_cog(paatuPetti(bot))
    
    @bot.event
    async def on_ready():
        print("Ready")

    @bot.listen("on_message")
    async def log(message):
        if not message.author.bot:
            if not message.guild:
                await message.reply("Enne ivide vilichit oru karyam illa!")
            else:
                print(message.content + " from " + message.author.name)
    
    bot.run(token)


if __name__ == "__main__":
    main()
