import math
from collections import deque

# Original symmetric circuit; dots are shared by both players.
MAP = ("################", "#......##......#", "#.##.#....#.##.#",
       "#....#.##.#....#", "###............#", "#...##....##...#",
       "#...##....##...#", "#............###", "#....#.##.#....#",
       "#.##.#....#.##.#", "#......##......#", "################")


class Circuit:
    def __init__(self):
        self.cells=[(1,1),(14,10)]
        self.dots={(x,y) for y,row in enumerate(MAP) for x,tile in enumerate(row) if tile=="."}
        self.dots.difference_update(self.cells)
        self.scores=[0,0]
        self.progress=[0.,0.]
        self.destination=self.cells[:]
        self.heading=[(1,0),(-1,0)]
        self.turn=self.heading[:]
        self.elapsed=0.
        self.steps=[0,0]

    def step(self,dt,inputs):
        self.elapsed+=dt
        arrivals=[]
        for side,keys in enumerate(inputs):
            dx,dy=keys[:2]
            fast=len(keys)>2 and keys[2]
            if dx or dy:
                self.turn[side]=(dx,0) if dx else (0,dy)
            travel=dt/(.083 if fast else .18)
            while travel>0:
                x,y=self.cells[side]
                if self.destination[side]==(x,y):
                    a,b=self.turn[side]
                    if not (fast and self.steps[side]%3==2) and MAP[y+b][x+a]==".":
                        self.heading[side]=self.turn[side]
                    a,b=self.heading[side]
                    if MAP[y+b][x+a]!=".":
                        break
                    self.destination[side]=(x+a,y+b)
                    self.steps[side]+=1
                remaining=1-self.progress[side]
                if travel<remaining:
                    self.progress[side]+=travel
                    break
                travel-=remaining
                self.cells[side]=self.destination[side]
                self.progress[side]=0.
                arrivals.append((side,self.cells[side]))
        for side,pos in arrivals:
            if pos in self.dots:
                self.scores[side]+=1
                self.dots.remove(pos)
        return self.elapsed>=30 or not self.dots

    def bot(self):
        start=self.destination[0]
        q=deque([(start,(0,0))]);seen={start}
        while q:
            (x,y),first=q.popleft()
            if (x,y)!=start and (x,y) in self.dots:return first
            for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                p=(x+dx,y+dy)
                if MAP[p[1]][p[0]]=="." and p not in seen:
                    seen.add(p);q.append((p,(dx,dy) if first==(0,0) else first))
        return (0,0)

    def snapshot(self):
        positions=[(x+(a-x)*t,y+(b-y)*t)
                   for (x,y),(a,b),t in zip(self.cells,self.destination,self.progress)]
        return dict(maze=True,dots=list(self.dots),cells=positions,scores=self.scores,
                    seconds=max(0,math.ceil(30-self.elapsed)))


def paint_maze(canvas,frame):
    w,h=canvas.winfo_width(),canvas.winfo_height()
    unit=min((w-12)/16,(h-90)/12)
    ox,oy=(w-16*unit)/2,(h-12*unit)/2
    for y,row in enumerate(MAP):
        for x,c in enumerate(row):
            if c=="#":
                a,b=ox+x*unit,oy+y*unit
                canvas.create_rectangle(a,b,a+unit,b+unit,fill="#292947",outline="#38385b")
    for x,y in frame["dots"]:
        a,b=ox+(x+.5)*unit,oy+(y+.5)*unit
        canvas.create_oval(a-2,b-2,a+2,b+2,fill="#ff3994",outline="")
    for i,(x,y) in enumerate(frame["cells"]):
        a,b=ox+(x+.5)*unit,oy+(y+.5)*unit;r=unit*(.26 if i else .38)
        canvas.create_polygon(a,b-r,a+r,b,a,b+r,a-r,b,fill=("#7b55ff","#c6fff4")[i])
    canvas.create_text(w/2,19,text="Контур   ·   %d с   |   Белые %d   /   Чёрные %d"%(frame["seconds"],*frame["scores"][::-1]),fill="white",font=("Segoe UI",12,"bold"))
    canvas.create_text(w/2,h-17,text="Собирайте точки · Shift ускоряет и удлиняет поворот",fill="#80e8df")
