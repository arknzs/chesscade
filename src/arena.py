import math
import random
import time
import tkinter as tk

INK = "#101020"
PAPER = "#f4edda"
MINT = "#6feae6"
GOLD = "#ffbd70"


def draw_danger_edges(canvas, x, y, scale, color=GOLD, inset=5):
    width,height=320*scale,192*scale
    edge=inset*scale
    for x0,y0,x1,y1 in [(x,y,x+width,y+edge),(x,y+height-edge,x+width,y+height),
                       (x,y+edge,x+edge,y+height-edge),(x+width-edge,y+edge,x+width,y+height-edge)]:
        canvas.create_rectangle(x0,y0,x1,y1,fill=color,outline="",stipple="gray50")
    canvas.create_rectangle(x,y,x+width,y+height,outline=color,width=2)


def movement_key(event):
    # Tk on Windows reports virtual key codes even with a Cyrillic layout.
    return {65:"a",68:"d",83:"s",87:"w"}.get(event.keycode,event.keysym.lower())


class Arena(tk.Canvas):
    def __init__(self, parent, event, done):
        super().__init__(parent, bg=INK, highlightthickness=0, takefocus=True)
        self.event, self.done = event, done
        self.rng = random.Random(event["seed"])
        self.keys = set()
        self.x, self.y = 160., 96.
        self.velocity=[0.,0.]
        self.waves = []
        self.boss = event.get("boss",self.rng.randrange(2))
        self.target = self.rng.uniform(.28, .73)
        self.phase = self.rng.uniform(0, 2)
        self.start = self.previous = time.monotonic()
        self.timer = None
        self.bind("<KeyPress>", self.key)
        self.bind("<KeyRelease>", lambda e: self.keys.discard(movement_key(e)))
        self.bind("<FocusOut>", lambda _: self.keys.clear())
        self.bind("<Button-1>", lambda _: self.strike())
        self.bind("<Destroy>", self.cancel)
        self.bind("<Map>",lambda _: self.focus_set())
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.focus_set()
        self.tick()

    def cancel(self, _):
        if self.timer:
            self.after_cancel(self.timer)
            self.timer = None

    def key(self, e):
        self.keys.add(movement_key(e))
        if e.keysym == "space":
            self.strike()

    def marker(self, elapsed):
        return .5 + .5 * math.sin(3.3 * elapsed + self.phase)

    def strike(self):
        self.focus_set()
        t = time.monotonic() - self.start
        if self.event["kind"] in ("qte","duel") and t > .3:
            self.done(abs(self.marker(t) - self.target) <= .15 and t < 5)

    def tick(self):
        self.timer = None
        now = time.monotonic()
        elapsed, dt = now - self.start, min(.05, now - self.previous)
        self.previous = now
        w, h = self.winfo_width(), self.winfo_height()
        self.delete("all")
        def label(y, s, size, color=PAPER, weight="normal"):
            self.create_text(w/2, y, text=s, font=("Segoe UI", size, weight), fill=color)
        if self.event["kind"] in ("qte","duel"):
            label(h*.25, ("ВЫЗОВ СОПЕРНИКА" if self.event["kind"]=="duel" else "Q T E    /    В З Я Т И Е"), 11, MINT, "bold")
            label(h*.37, "Поймай момент", 26, weight="bold")
            left, span, y = w*.12, w*.76, h*.54
            self.create_rectangle(left,y,left+span,y+16, fill="#384b47", outline="")
            self.create_rectangle(left+(self.target-.15)*span,y,left+(self.target+.15)*span,y+16, fill=MINT, outline="")
            marker = left + self.marker(elapsed)*span
            self.create_line(marker,y-9,marker,y+25, fill=GOLD,width=4)
            label(h*.68, "Пробел или щелчок в зелёной зоне", 12)
            label(h*.77, "%.1f с" % max(0,5-elapsed), 12, GOLD)
            if elapsed >= 5:
                self.done(False)
                return
        else:
            label(h*.13, ["Стекольщик","Маятник"][self.boss], 24, weight="bold")
            label(h*.22, "Уклоняйся стрелками или WASD", 12, MINT)
            scale = min(w*.87/320, h*.48/192)
            ox, oy = (w-320*scale)/2, h*.31
            def box(x,y,a,b,color):
                self.create_rectangle(ox+x*scale,oy+y*scale,ox+a*scale,oy+b*scale,fill=color,outline="")
            box(0,0,320,192,"#1d302d")
            dx = int(bool(self.keys & {"right","d"}))-int(bool(self.keys & {"left","a"}))
            dy = int(bool(self.keys & {"down","s"}))-int(bool(self.keys & {"up","w"}))
            fast=self.event.get("sprint",True) and bool(self.keys & {"shift_l","shift_r"})
            for i,d in enumerate((dx,dy)):
                target=d*(285 if fast else 154)/max(1,math.hypot(dx,dy))
                self.velocity[i]+=(target-self.velocity[i])*min(1,dt*(5.5 if fast else 24))
            self.x+=self.velocity[0]*dt
            self.y+=self.velocity[1]*dt
            if not(6<self.x<314 and 6<self.y<186):
                self.done(False)
                return
            age = elapsed - 1.3
            if age >= 0:
                while len(self.waves) <= int(age/1.48):
                    vertical = self.boss == 0 or len(self.waves)%2 == 0
                    self.waves.append((vertical,self.rng.uniform(49, (320 if vertical else 192)-49)))
                for i,(vertical,gap) in enumerate(self.waves):
                    pos = (age-i*1.48)*132-12
                    limit = 192 if vertical else 320
                    if pos > limit: continue
                    parts = [(0,pos,gap-39,pos+9),(gap+39,pos,320,pos+9)] if vertical else [(pos,0,pos+9,gap-39),(pos,gap+39,pos+9,192)]
                    for x,y,a,b in parts:
                        box(x,y,a,b,GOLD)
                        if x-5 < self.x < a+5 and y-5 < self.y < b+5:
                            self.done(False)
                            return
            draw_danger_edges(self,ox,oy,scale,inset=6)
            cx,cy,r = ox+self.x*scale,oy+self.y*scale,6*scale
            self.create_polygon(cx,cy-r,cx+r,cy,cx,cy+r,cx-r,cy,fill=MINT)
            label(h*.88,"До конца волны   %.1f с" % max(0,9-elapsed),12,GOLD)
            if elapsed >= 9:
                self.done(True)
                return
        self.timer = self.after(16,self.tick)
