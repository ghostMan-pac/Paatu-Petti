class langSupport():
    
    def __init__(self, ctx) -> None:
        self.ctx = ctx
        self.malayalam = ''
        self.english = ''
        
    def matchErrorMessage(self):
        self.malayalam = 'പൊരുത്തപ്പെടുന്ന ഒന്നും കണ്ടെത്താനായില്ല'
        self.english = 'Couldn\'t find anything that matches'
        return self.returnLang()
    
    def fetchErrorMessage(self):
        self.malayalam = 'കൊണ്ടുവരാനായില്ല'
        self.english = 'Unable to fetch'
        return self.returnLang()
    
    def defaultError(self):
        self.malayalam = 'ഒരു തെറ്റ്‌ സംഭവിച്ചു:'
        self.english = 'An error occured:'
        return self.returnLang()
    
    def durationMessage(self):
        self.malayalam = ['ദിവസങ്ങളിൽ','മണിക്കൂറുകൾ','മിനിയൂട്ടുകൾ','നിമിഷം']
        self.english = ['Days', 'Hours', 'Minutes', 'Seconds']
        return self.returnLang()

    def embedStrings(self):
        self.malayalam = ['ഇപ്പോഴത്തെ ഗാനം', 'ദൈര്‍ഖ്യം', 'അഭ്യര്‍ത്ഥന', 'അപ്‌ലോഡർ']
        self.english = ['Track', 'Duration', 'Requested By', 'Uploader']
        return self.returnLang()

    def DMMessage(self):
        self.malayalam = 'ഈ കമാൻഡ് ഒരു DM ചാനലിൽ ഉപയോഗിക്കാൻ കഴിയില്ല'
        self.english = 'You cannot use this command in a DM channel'
        return self.returnLang()
    
    def voiceChannelError(self):
        self.malayalam = 'ഞാൻ ഒരു ചാനലിൽ പ്രവേശിച്ചിട്ടില്ല'
        self.english = 'I haven\'t joined a channel'
        return self.returnLang()
    
    def noSongError(self):
        self.malayalam = 'പാട്ട് ഒന്നും പ്ലേ ചെയ്യുന്നില്ല'
        self.english = 'No song is currently playing'
        return self.returnLang()
    
    def volumeError(self):
        self.malayalam = 'വോളിയം 0 നും 100 നും ഇടയിൽ ക്രമീകരിക്കണം'
        self.english = 'Volume must be between 0 and 100'
        return self.returnLang()
    
    def volumeSetMessage(self, vol):
        self.malayalam = 'വോളിയം {}ആയി സജ്ജമാക്കി'.format(vol)
        self.english = 'Volume has been set to {}'.format(vol)
        return self.returnLang()
    
    
    def requestError(self):
        self.malayalam = 'ഈ അഭ്യർത്ഥന പ്രോസസ്സ് ചെയ്യുമ്പോൾ ഒരു പിശക് സംഭവിച്ചു:'
        self.english = 'This request was unable to be processed due to an error: '
        return self.returnLang()
    
    def noQueueError(self):
        self.malayalam = 'ക്യൂ ശൂന്യമാണ്'
        self.english = 'No songs in queue'
        return self.returnLang()
        
    def addedToQueue(self):
        self.malayalam = 'ക്യൂവിലേക്ക് ചേർത്തു:'
        self.english = 'Added to queue:'
        return self.returnLang()
    
    def alreadyInVoiceError(self):
        self.malayalam = 'ഞാൻ ഇവിടെയുണ്ട്'
        self.english = 'Im in a voice channel'
        return self.returnLang()
    
    def channelJoinError(self):
        self.malayalam = 'പൊയ് ചാനൽ ജോയിൻ ചെയു'
        self.english = 'please join a voice channel'
        return self.returnLang()
    
    def returnLang(self):
        switch = {
            'en':self.english,
            'mal':self.malayalam
        }
        return switch.get(self.ctx.voice_states.lang)
