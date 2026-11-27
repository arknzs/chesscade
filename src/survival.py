from circuit import paint_maze
import math
import random
import tkinter as tk

from arena import INK, GOLD, MINT, PAPER, movement_key, draw_danger_edges


class Survival:
    """Both players face the same walls on one host clock."""
    def __init__(self, seed, expanded=False, practice=False):
        self.rng = random.Random(seed)
        self.pattern = self.rng.randrange(6 if expanded else 2)
        self.velocity=[[0.,0.],[0.,0.]]
        self.circle_count=self.rng.randint(8,12)
        self.total_time=self.circle_count
        self.active_sides=(1,) if practice else (0,1)
        self.progress=[0,0]
        self.enter_targets=[(160,96)]
        for _ in range(self.circle_count):
            while True:
                point=(self.rng.randint(45,275),self.rng.randint(40,152))
                if math.dist(point,self.enter_targets[-1])>=78:
                    self.enter_targets.append(point)
                    break
        self.circle_centers=[(160,96)]*2
        self.players = [[160.,96.], [160.,96.]]
        self.walls = []
        self.elapsed = 0.
        self.next_wave = 2.
        self.wave = 0

    @property
    def complete(self):
        return self.pattern>=4 and all(self.progress[side]>=self.circle_count for side in self.active_sides)

    def exiting(self,side):
        return self.pattern==5 and self.progress[side]%2==0

    def circle_target(self,side):
        if self.pattern==5:
            return self.circle_centers[side]
        return self.enter_targets[min(self.progress[side]+1,self.circle_count)]

    def step(self, dt, directions, *, clock_dt=None):
        if self.complete:
            return []
        self.elapsed += clock_dt if self.pattern>=4 and clock_dt is not None else dt
        if self.pattern<4 and self.elapsed >= self.next_wave:
            vertical = self.pattern == 0 or (self.pattern in (1,3) and self.wave % 2 == 0)
            limit = 320 if vertical else 192
            self.walls.append([vertical, -10., self.rng.uniform(40, limit-40)])
            self.next_wave += 1.7
            self.wave += 1
        for wall in self.walls:
            if self.pattern==3: wall[2]+=math.sin(self.elapsed*3)*40*dt
            wall[1] += (82 + min(55,self.elapsed/2))*dt
        self.walls = [w for w in self.walls if w[1] < (192 if w[0] else 320)+6]
        dead = []
        for side in self.active_sides:
            if self.pattern>=4 and self.progress[side]>=self.circle_count:
                continue
            keys=directions[side]
            dx,dy=keys[:2]
            fast=len(keys)>2 and keys[2]
            p=self.players[side]
            length=max(1,math.hypot(dx,dy))
            for axis,d in enumerate((dx,dy)):
                vel=self.velocity[side]
                target=d*(285 if fast else 148)/length
                vel[axis]+=(target-vel[axis])*min(1,dt*(5.5 if fast else 24))
                p[axis]+=vel[axis]*dt
            if not (5<p[0]<315 and 5<p[1]<187):
                dead.append(side)
                continue
            for vertical,pos,gap in self.walls:
                across,along=p if vertical else p[::-1]
                if pos-5 <= along <= pos+14 and abs(across-gap)>=30:
                    dead.append(side)
                    break
            if self.pattern>=4:
                if self.elapsed>=self.total_time:
                    dead.append(side)
                    continue
                exiting=self.exiting(side)
                if exiting:
                    x,y=self.circle_centers[side]
                    distance=math.dist(p,(x,y))
                    if distance:
                        fraction=min(1,32*dt/distance)
                        self.circle_centers[side]=(x+(p[0]-x)*fraction,y+(p[1]-y)*fraction)
                inside=math.dist(p,self.circle_target(side))<35
                if inside!=exiting:
                    self.progress[side]+=1
                    if self.pattern==5 and self.progress[side]<self.circle_count:
                        if self.exiting(side):
                            self.circle_centers[side]=tuple(p)
                        else:
                            x,y=p
                            next_x=x+85 if x<160 else x-85
                            self.circle_centers[side]=(next_x,min(148,max(44,y)))
        return dead

    def bot(self):
        if self.pattern>=4:
            x,y=self.players[0]
            if self.progress[0]>=self.circle_count:return (0,0)
            a,b=self.circle_target(0)
            if self.exiting(0):
                a,b=(240 if x<160 else 80),(142 if y<96 else 50)
            return (int(a>x+3)-int(a<x-3),int(b>y+3)-int(b<y-3))
        for vertical,pos,gap in self.walls:
            across,along=self.players[0] if vertical else self.players[0][::-1]
            if pos<=along+5:
                delta=gap-across
                # The computer reacts late to some waves.
                if self.wave%4==0 and pos<along-12: return (0,0)
                direction=0 if abs(delta)<5 else (1 if delta>0 else -1)
                return (direction,0) if vertical else (0,direction)
        return (0,0)

    def snapshot(self):
        return dict(players=[p[:] for p in self.players],walls=[w[:] for w in self.walls],
                    pattern=self.pattern,targets=[self.circle_target(side) for side in (0,1)],
                    progress=self.progress[:],circle_count=self.circle_count,
                    seconds_left=max(0.,self.total_time-self.elapsed))


class DuelView(tk.Canvas):
    def __init__(self, parent, role):
        super().__init__(parent,bg=INK,highlightthickness=0,takefocus=True)
        self.keys=set()
        self.role=role
        self.sprint=True
        self.bind("<KeyPress>",lambda e:self.keys.add(movement_key(e)))
        self.bind("<KeyRelease>",lambda e:self.keys.discard(movement_key(e)))
        self.bind("<FocusOut>",lambda _:self.keys.clear())
        self.bind("<Button-1>",lambda _:self.focus_set())
        self.bind("<Map>",lambda _: self.focus_set())
        self.place(relwidth=1,relheight=1)
        self.focus_set()

    def direction(self, side):
        left,right,up,down=("a","d","w","s") if side or self.role!="local" else ("left","right","up","down")
        keys=self.keys
        dx=int(right in keys)-int(left in keys)
        dy=int(down in keys)-int(up in keys)
        if self.role!="local":
            dx=max(-1,min(1,dx+int("right" in keys)-int("left" in keys)))
            dy=max(-1,min(1,dy+int("down" in keys)-int("up" in keys)))
        return dx,dy,int(self.sprint and (("shift_l" in keys if side else "shift_r" in keys) if self.role=="local" else bool(keys & {"shift_l","shift_r"})))

    def paint(self, frame):
        self.delete("all")
        if frame.get("maze"):
            paint_maze(self,frame)
            return
        w,h=self.winfo_width(),self.winfo_height()
        scale=min(w*.90/320,h*.65/192)
        x,y=(w-320*scale)/2,(h-192*scale)/2
        def box(a,b,c,d,color):
            self.create_rectangle(x+a*scale,y+b*scale,x+c*scale,y+d*scale,fill=color,outline="")
        circle_mode=frame["pattern"]>=4
        box(0,0,320,192,"#294138")
        accent=GOLD
        if circle_mode:
            viewer=0 if self.role=="guest" else 1
            accent=GOLD if frame["pattern"]==5 and frame["progress"][viewer]%2==0 else MINT
            count=frame["circle_count"]
            sides=(0,1) if self.role=="local" else (0,) if self.role=="guest" else (1,)
            right=x+320*scale
            badge_y=y-12
            badges=[]
            for side in sides:
                progress=frame["progress"][side]
                a,b=frame["targets"][side]
                if progress<count:
                    self.create_oval(x+(a-35)*scale,y+(b-35)*scale,x+(a+35)*scale,y+(b+35)*scale,
                                     outline=GOLD if frame["pattern"]==5 and progress%2==0 else MINT,width=3,dash=(5,3) if len(sides)==2 and not side else ())
                counter=f"{progress:02d} / {count:02d}"
                badges.append(("● " if side==0 else "○ ") + counter if len(sides)==2 else counter)
            seconds=math.ceil(frame["seconds_left"]*10)/10
            time_color=GOLD if seconds<=5 else accent
            self.create_rectangle(x,badge_y-32,x+78,badge_y,fill="#26213b",outline=time_color)
            self.create_text(x+39,badge_y-16,text=f"{seconds:.1f} с",
                             fill=time_color,font=("Consolas",13,"bold"))
            width=160 if len(sides)==2 else 78
            self.create_rectangle(right-width,badge_y-32,right,badge_y,fill="#26213b",outline=accent)
            self.create_text(right-width/2,badge_y-16,text="  ".join(badges),
                             fill=accent,font=("Consolas",13,"bold"))
        else:
            title=("Стекольщик","Маятник","Поперечный поток","Дрейф")[frame["pattern"]]
            self.create_text(w/2,h*.1,text=title+" · избегайте стен и краёв",fill=PAPER,font=("Segoe UI",16,"bold"))
        for v,pos,gap in frame["walls"]:
            if v:
                box(0,pos,gap-35,pos+9,GOLD);box(gap+35,pos,320,pos+9,GOLD)
            else:
                box(pos,0,pos+9,gap-35,GOLD);box(pos,gap+35,pos+9,192,GOLD)
        draw_danger_edges(self,x,y,scale,accent)
        for side,(px,py) in enumerate(frame["players"]):
            if self.role=="practice" and not side:continue
            r=5 if side else 8
            self.create_oval(x+(px-r)*scale,y+(py-r)*scale,x+(px+r)*scale,y+(py+r)*scale,
                             fill=PAPER if side else "#142522",outline=MINT,width=2)
        if circle_mode:return
        hint="Белые — WASD   ·   Чёрные — стрелки" if self.role=="local" else "Уклоняйтесь стрелками или WASD"
        self.create_text(w/2,h*.91,text=hint,fill=MINT,font=("Segoe UI",11))
