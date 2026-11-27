import tkinter as tk

from arena import MINT, PAPER


def hearts(parent,side,count):
    c=tk.Canvas(parent,width=220,height=25,bg=parent.cget("bg"),highlightthickness=0)
    c.pack(anchor="center")
    c.create_text(1,12,text=side,anchor="w",fill="#eeecff",font=("Segoe UI",11))
    for i in range(5):
        for y,row in enumerate(("0110110","1111111","1111111","0111110","0011100","0001000")):
            for x,k in enumerate(row):
                if k=="1":
                    a,b=72+i*24+x*3,3+y*3
                    c.create_rectangle(a,b,a+3,b+3,outline="",fill="#ff3788" if i<count else "#483147")


class VolumeSlider(tk.Canvas):
    """A volume slider with mouse and keyboard control."""

    inset = 9
    track_y = 37

    def __init__(self, parent, value, on_change, *, muted=False):
        super().__init__(parent, width=158, height=49, bg=parent.cget("bg"),
                         bd=0, highlightthickness=0, cursor="hand2", takefocus=True)
        self.value = value
        self.on_change = on_change
        self.muted = muted
        for event in ("<Configure>", "<FocusIn>", "<FocusOut>"):
            self.bind(event, lambda _: self.draw())
        self.bind("<Button-1>", self.point)
        self.bind("<B1-Motion>", self.point)
        for key, change in (("Left", -1), ("Down", -1), ("Right", 1), ("Up", 1),
                            ("Prior", 10), ("Next", -10)):
            self.bind(f"<{key}>", lambda event, delta=change: self.set_level(self.value.get() + delta))
        self.bind("<Home>", lambda _: self.set_level(0))
        self.bind("<End>", lambda _: self.set_level(100))

    def set_muted(self, muted):
        if self.muted != muted:
            self.muted = muted
            self.draw()

    def point(self, event):
        self.focus_set()
        span = max(1, self.winfo_width() - 2*self.inset)
        return self.set_level(round(100*(event.x-self.inset)/span))

    def set_level(self, level):
        level = min(100, max(0, level))
        if self.value.get() != level:
            self.value.set(level)
            self.draw()
            self.on_change()
        return "break"

    def draw(self):
        self.delete("all")
        left, right = self.inset, self.winfo_width()-self.inset
        if right <= left:
            return
        level = self.value.get()
        x = left + (right-left)*level/100
        y = self.track_y
        accent = "#b8a5d8" if self.muted else MINT
        bloom = "#453653" if self.muted else "#27545b"

        self.create_text(2, 12, text="Громкость", anchor="w", fill=PAPER, font=("Segoe UI", 9))
        self.create_line(right-34, 12, right-2, 12, width=21, capstyle="round", fill="#332842")
        self.create_text(right-18, 12, text=f"{level}%", fill=accent, font=("Consolas", 10, "bold"))

        self.create_line(left, y, right, y, width=5, capstyle="round", fill="#493660")
        if level:
            self.create_line(left, y, x, y, width=8, capstyle="round", fill=bloom)
            self.create_line(left, y, x, y, width=4, capstyle="round", fill=accent)
        self.create_oval(x-9, y-9, x+9, y+9, outline=accent if self.focus_get() == self else bloom, width=2)
        self.create_oval(x-5, y-5, x+5, y+5, fill=accent, outline="")


class NeonCheck(tk.Canvas):
    def __init__(self, parent, text, variable):
        super().__init__(parent, width=260, height=30, bg=parent.cget("bg"),
                         bd=0, highlightthickness=0, cursor="hand2", takefocus=True)
        self.text = text
        self.variable = variable
        self.hover = False
        for event in ("<Configure>", "<FocusIn>", "<FocusOut>"):
            self.bind(event, lambda _: self.draw())
        self.bind("<Enter>", lambda _: self.set_hover(True))
        self.bind("<Leave>", lambda _: self.set_hover(False))
        self.bind("<ButtonRelease-1>", self.toggle)
        self.bind("<space>", self.toggle)
        self.bind("<Return>", self.toggle)

    def set_hover(self, hover):
        self.hover = hover
        self.draw()

    def toggle(self, event):
        self.focus_set()
        if event.type == tk.EventType.ButtonRelease:
            if not (0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()):
                return "break"
        self.variable.set(not self.variable.get())
        self.draw()
        return "break"

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 20 or h <= 18:
            return
        checked = self.variable.get()
        focus = self.focus_get() == self
        row_fill = "#3a2e51" if self.hover else "#312642" if checked else "#29243b"
        self.create_rectangle(1, 1, w-1, h-1, fill=row_fill, outline=MINT if focus else row_fill)
        self.create_text(11, h/2, text=self.text, anchor="w", fill=PAPER, font=("Segoe UI", 10))

        x, y = w-20, h/2
        mark = MINT if checked else "#766389"
        self.create_rectangle(x-8, y-8, x+8, y+8, fill=MINT if checked else "#211b31", outline=mark)
        if checked:
            self.create_line(x-4, y, x-1, y+3, x+4, y-3, fill="#142b34",
                             width=2, capstyle="round", joinstyle="round")
