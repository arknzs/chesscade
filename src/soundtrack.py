import json
import random
from pathlib import Path

from pygame import error, mixer


class Soundtrack:
    def __init__(self, settings):
        self.settings=settings
        self.enabled=True
        self.volume=35
        try:
            data=json.loads(settings.read_text(encoding="utf8"))
            self.enabled=data["enabled"] is not False
            self.volume=max(0,min(100,int(data["volume"])))
        except (OSError,ValueError,KeyError,TypeError):
            pass
        directory=Path(__file__).resolve().parent
        if not (directory/"music").is_dir():
            directory=directory.parent
        else:
            directory=directory/"music"
        self.tracks=sorted(directory.glob("ambient*.wav"))
        self.queue=[]
        self.last=None
        self.available=False
        self.paused=False

    def configure(self,enabled,volume):
        self.enabled=enabled
        self.volume=volume
        if self.available:
            mixer.music.set_volume(volume/100 if enabled else 0)
        try:
            self.settings.parent.mkdir(parents=True,exist_ok=True)
            self.settings.write_text(json.dumps(dict(enabled=enabled,volume=volume)),encoding="utf8")
        except OSError:
            pass

    def next_track(self):
        if not self.queue:
            self.queue=self.tracks[:]
            random.shuffle(self.queue)
            if len(self.queue)>1 and self.queue[-1]==self.last:
                self.queue[-1],self.queue[0]=self.queue[0],self.queue[-1]
        return self.queue.pop()

    def tick(self,external=False):
        if not self.tracks:
            return
        if not self.available:
            try:
                mixer.init()
            except error:
                self.tracks=[]
                return
            self.available=True
        if external:
            if mixer.music.get_busy():
                mixer.music.pause()
                self.paused=True
            return
        if self.paused:
            mixer.music.unpause()
            self.paused=False
        if not mixer.music.get_busy():
            for _ in range(len(self.tracks)):
                track=self.next_track()
                try:
                    mixer.music.load(str(track))
                    mixer.music.set_volume(self.volume/100 if self.enabled else 0)
                    mixer.music.play()
                    self.last=track
                    return
                except error:
                    continue
            self.tracks=[]

    def close(self):
        if self.available:
            mixer.quit()
