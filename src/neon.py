def hearts(parent,side,count):
    import tkinter as tk
    c=tk.Canvas(parent,width=220,height=25,bg=parent.cget("bg"),highlightthickness=0)
    c.pack(anchor="center")
    c.create_text(1,12,text=side,anchor="w",fill="#eeecff",font=("Segoe UI",11))
    for i in range(5):
        for y,row in enumerate(("0110110","1111111","1111111","0111110","0011100","0001000")):
            for x,k in enumerate(row):
                if k=="1":
                    a,b=72+i*24+x*3,3+y*3
                    c.create_rectangle(a,b,a+3,b+3,outline="",fill="#ff3788" if i<count else "#483147")


def piece(c,x,y,cell,p):
    fill,edge=("#eef3ff","#47406d") if p.color else ("#19132e","#aa94d9")
    outlines=[
        [(30,78),(39,54),(40,46),(32,37),(36,24),(50,18),(64,24),(68,37),(60,46),(61,54),(70,78)],
        [(23,78),(34,59),(57,43),(39,42),(31,51),(19,44),(32,24),(47,21),(52,12),(66,22),(78,46),(72,78)],
        [(26,78),(40,55),(30,41),(35,30),(52,12),(48,36),(58,24),(69,39),(60,55),(74,78)],
        [(25,78),(32,47),(24,39),(24,19),(35,19),(35,29),(44,29),(44,19),(55,19),(55,29),(64,29),(64,19),(75,19),(75,39),(68,47),(75,78)],
        [(30,78),(35,51),(20,23),(42,36),(50,13),(59,36),(80,23),(65,51),(70,78)],
        [(28,78),(37,54),(29,37),(44,32),(45,25),(35,25),(35,17),(45,17),(45,9),(55,9),(55,17),(65,17),(65,25),(55,25),(56,32),(71,37),(63,54),(72,78)]]
    pts=[v for a,b in outlines[p.piece_type-1] for v in (x+cell*a/100,y+cell*b/100)]
    c.create_polygon(*pts,fill=fill,outline=edge,width=1)
    c.create_rectangle(x+.23*cell,y+.79*cell,x+.77*cell,y+.84*cell,fill=fill,outline=edge)
