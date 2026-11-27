import json
from soundtrack import Soundtrack
from circuit import Circuit
from neon import NeonCheck, VolumeSlider, hearts
from pieces import PieceSet
import os
import queue
import random
import shutil
import socket
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import chess
import chess.engine
from PIL import Image, ImageTk
import subprocess
from concurrent.futures import ThreadPoolExecutor

LEVELS = {"Новичок": (0, .08), "Клубный": (7, .25), "Эксперт": (15, .65), "Мастер": (20, 1.5)}

def computer_move(board, level):
    skill, seconds = LEVELS[level]
    binary = Path(__file__).resolve().parent/"engine/stockfish.exe"
    with chess.engine.SimpleEngine.popen_uci(str(binary), creationflags=subprocess.CREATE_NO_WINDOW) as engine:
        engine.configure({"Skill Level":skill})
        return engine.play(board,chess.engine.Limit(time=seconds)).move.uci()
from arena import Arena, GOLD, INK, MINT, PAPER
from encounter import launch
from link import Link, PORT
from survival import Survival, DuelView
from match import Match, MAX_ENERGY

CARD, MUTED, LINE = "#1b1930", "#b8b1d2", "#39334f"
MODES = ["С компьютером", "Вдвоём за доской", "Создать LAN-стол", "Войти по IP"]
RATES={"Очень редко":(52,68),"Редко":(42,58),"Обычно":(32,48),"Часто":(22,38),"Очень часто":(12,28),"Выкл.":(0,0)}


def label(parent, text, size=11, color=PAPER, bold=False):
    return tk.Label(parent, text=text, fg=color, bg=parent.cget("bg"), anchor="center",
                    justify="center", font=("Segoe UI",size,"bold" if bold else "normal"))


def button(parent, text, command, primary=False):
    return tk.Button(parent, text=text, command=command, relief="flat", bd=0,
                     bg=MINT if primary else "#493660", fg=INK if primary else PAPER,
                     activebackground=GOLD, activeforeground=INK, cursor="hand2",
                     padx=12, pady=7, font=("Segoe UI",10,"bold"))


def text_block(parent,text,size=11,color=PAPER,width=650):
    return tk.Label(parent,text=text,font=("Segoe UI",size),bg="#26213b",fg=color,
                    justify="center",wraplength=width,padx=14,pady=8)


def option_picker(parent, value, options, columns):
    panel=tk.Frame(parent,bg=CARD)
    for index,name in enumerate(options):
        row,col=divmod(index,columns)
        panel.columnconfigure(col,weight=1,uniform="options")
        item=tk.Radiobutton(panel,text=name,variable=value,value=name,indicatoron=False,
                            relief="flat",offrelief="flat",overrelief="flat",bd=0,
                            bg=LINE,fg=PAPER,selectcolor="#68316e",
                            activebackground="#4f4167",activeforeground=MINT,
                            highlightthickness=1,highlightbackground=CARD,highlightcolor=MINT,
                            font=("Segoe UI",9),cursor="hand2",padx=4,pady=4)
        item.grid(row=row,column=col,sticky="ew",padx=1,pady=1)
    return panel


class PartyMenu:
    def __init__(self, parent):
        self.popup=tk.Menu(parent,tearoff=False,bg=CARD,fg=PAPER,
                           activebackground="#68316e",activeforeground=PAPER,
                           disabledforeground=MUTED,relief="flat",bd=0,
                           font=("Segoe UI",10))
        self.trigger=button(parent,"Партия  ▾",self.open)

    def screen(self,title):
        self.popup.delete(0,"end")
        if title is None:
            self.trigger.pack_forget()
        else:
            self.trigger.configure(text=title+"  ▾")
            self.trigger.pack(side="right",padx=14)

    def open(self):
        try:
            self.popup.tk_popup(self.trigger.winfo_rootx(),
                                self.trigger.winfo_rooty()+self.trigger.winfo_height())
        finally:
            self.popup.grab_release()

    def __getattr__(self,name):
        return getattr(self.popup,name)


class App:
    def __init__(self, root):
        self.root = root
        root.title("Chesscade")
        root.iconbitmap(str(Path(__file__).with_name("chesscade.ico")))
        with Image.open(Path(__file__).with_name("chesscade-logo.png")) as logo:
            logo.thumbnail((292,75),Image.Resampling.LANCZOS)
            self.logo=ImageTk.PhotoImage(logo,master=root)
        root.geometry("1050x735")
        root.minsize(825,650)
        root.configure(bg=INK)
        self.role = None
        self.level=tk.StringVar(value="Клубный")
        self.worker=ThreadPoolExecutor(max_workers=1)
        self.search=None
        self.mode = tk.StringVar(value=MODES[0])
        self.rate = tk.StringVar(value="Обычно")
        self.qte = tk.BooleanVar(value=True)
        self.sprint=tk.BooleanVar(value=True)
        self.variants=[tk.BooleanVar(value=True) for _ in range(6)]
        self.circuit=tk.BooleanVar(value=False)
        self.motion=tk.BooleanVar(value=True)
        local_data=Path(os.environ["LOCALAPPDATA"])
        profile=local_data/"Chesscade"
        legacy_profile=local_data/"Gambit67"
        for name in ("preferences.json","music.json"):
            previous=legacy_profile/name
            destination=profile/name
            if previous.is_file() and not destination.exists():
                try:
                    profile.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(previous,destination)
                except OSError:
                    pass
        self.config_path=profile/"preferences.json"
        self.encounter_path=local_data/"ChesscadeEncounters"
        legacy_encounters=local_data/"Gambit67Encounters"
        main_class="build/classes/java/main/Main.class"
        if not (self.encounter_path/main_class).is_file() and (legacy_encounters/main_class).is_file():
            self.encounter_path=legacy_encounters
        self.music=Soundtrack(self.config_path.with_name("music.json"))
        self.music_enabled=tk.BooleanVar(value=self.music.enabled)
        self.music_volume=tk.IntVar(value=self.music.volume)
        try:
            prefs=json.loads(self.config_path.read_text(encoding="utf8"))
            if prefs.get("rate") in RATES:self.rate.set(prefs["rate"])
            for key,var in [("maze",self.circuit),("motion",self.motion),("capture",self.qte),("sprint",self.sprint)]:
                if type(prefs.get(key)) is bool:var.set(prefs[key])
            selected=prefs.get("variants")
            if isinstance(selected,list) and any(i in selected for i in range(6)):
                for i,var in enumerate(self.variants):var.set(i in selected)
        except (OSError,ValueError,AttributeError): pass
        self.external_path = None
        self.link = self.game = self.state = self.arena = self.proc = None
        self.encounter_dir = None
        self.active_event = self.selected = None
        self.board = chess.Board()
        self.deadline = self.bot_at = float("inf")
        self.banner = tk.Frame(root,bg=INK)
        self.banner.pack(fill="x",padx=26,pady=(17,12))
        label(self.banner,"◈",23,MINT,True).pack(side="left")
        label(self.banner,"  Chesscade",18,PAPER,True).pack(side="left")
        label(self.banner,"ШАХМАТЫ   /   АРКАДА",9,MUTED,True).pack(side="right")
        self.menu_page = None
        self.duel=None
        self.maze_active=False
        self.training = False
        self.retry=tk.BooleanVar(value=False)
        self.drill_job=None
        self.body = body = tk.Frame(root,bg=INK)
        body.pack(fill="both",expand=True,padx=24,pady=(0,20))
        self.side = tk.Frame(body,bg=CARD,width=265,padx=17,pady=14)
        self.side.pack(side="right",fill="y",padx=(14,0))
        self.side.pack_propagate(False)
        self.play = tk.Frame(body,bg=INK)
        self.play.pack(side="left",fill="both",expand=True)
        self.upper = label(self.play,"●   Чёрные",12,MUTED,True)
        self.upper.pack(anchor="center",pady=(1,4))
        self.surface = tk.Frame(self.play,bg=INK)
        self.surface.pack(fill="both",expand=True)
        self.canvas = tk.Canvas(self.surface,bg=INK,highlightthickness=0)
        self.canvas.pack(fill="both",expand=True)
        self.pieces=PieceSet(self.canvas)
        self.canvas.bind("<Configure>",lambda _: self.draw())
        self.premove=None
        self.canvas.bind("<Button-1>",self.click)
        self.canvas.bind("<Button-3>",self.cancel_premove)
        root.bind("<Escape>",self.cancel_premove)
        self.lower = label(self.play,"○   Белые",12,PAPER,True)
        self.lower.pack(anchor="center",pady=(4,0))
        self.nav=PartyMenu(self.banner)
        self.home()
        root.protocol("WM_DELETE_WINDOW",self.close)
        root.after(50,self.poll)

    def alert(self,title,text):
        self.dialog(title,text,"OK")

    def ask(self,title,text):
        return self.dialog(title,text,"Подтвердить",cancel=True)

    def prompt(self,title,text,initialvalue="",parent=None):
        return self.dialog(title,text,"OK",cancel=True,initial=initialvalue)

    def dialog(self,title,text,accept,*,cancel=False,initial=None):
        win=tk.Toplevel(self.root,bg=CARD,padx=22,pady=18)
        win.title(title)
        win.transient(self.root)
        win.resizable(False,False)
        label(win,title,16,MINT,True).pack(anchor="center",pady=(0,8))
        label(win,text).pack(anchor="center",fill="x")
        win.winfo_children()[-1].configure(wraplength=380)
        result=None
        entry=None
        if initial is not None:
            entry=tk.Entry(win,bg=LINE,fg=PAPER,insertbackground=PAPER,relief="flat",font=("Segoe UI",11))
            entry.pack(fill="x",pady=10,ipady=5)
            entry.insert(0,initial)
            entry.select_range(0,"end")
        def confirm():
            nonlocal result
            result=entry.get() if entry is not None else True
            win.destroy()
        actions=tk.Frame(win,bg=CARD)
        actions.pack(fill="x",pady=(12,0))
        okay=button(actions,accept,confirm,True)
        okay.grid(row=0,column=2 if cancel else 1,padx=4)
        actions.columnconfigure(0,weight=1)
        actions.columnconfigure(3 if cancel else 2,weight=1)
        if cancel:
            button(actions,"Отмена",win.destroy).grid(row=0,column=1,padx=4)
        win.bind("<Return>",lambda _:confirm())
        win.bind("<Escape>",lambda _:win.destroy())
        win.update_idletasks()
        win.geometry("+%d+%d"%(self.root.winfo_rootx()+40,self.root.winfo_rooty()+65))
        win.grab_set()
        (entry or okay).focus_set()
        self.root.wait_window(win)
        return result

    def page(self,title):
        if self.drill_job is not None:
            self.root.after_cancel(self.drill_job)
            self.drill_job=None
        self.nav.screen(title)
        if self.menu_page:
            self.menu_page.destroy()
        self.menu_page=tk.Frame(self.body,bg=CARD,padx=22,pady=18)
        self.menu_page.place(relwidth=1,relheight=1)
        return self.menu_page

    def menu_backdrop(self,page):
        page.configure(padx=0,pady=0,bg=INK)
        glow=tk.Canvas(page,bg=INK,highlightthickness=0)
        glow.place(relwidth=1,relheight=1)

        def paint(offset):
            glow.delete("all")
            w,h=glow.winfo_width(),glow.winfo_height()
            for x in range(-h-180,w+180,180):
                for j,color in [(0,"#251b3d"),(8,"#392049"),(18,"#173639")]:
                    start=x+offset+j
                    glow.create_line(start,h,start+h,0,fill=color,width=2)

        job=None
        def animate():
            nonlocal job
            paint(int(time.monotonic()*38)%180)
            job=glow.after(40,animate)

        def cancel(_):
            if job is not None:
                glow.after_cancel(job)

        if self.motion.get():
            job=glow.after_idle(animate)
            glow.bind("<Destroy>",cancel)
        else:
            glow.bind("<Configure>",lambda _:paint(0))

    def home(self):
        page=self.page(None)
        self.menu_backdrop(page)
        menu=tk.Frame(page,bg=CARD,padx=28,pady=22,highlightbackground="#493660",highlightthickness=1)
        menu.place(relx=.5,rely=.5,anchor="center")
        tk.Label(menu,image=self.logo,bg=CARD,bd=0).pack(pady=(0,16))
        for title,action in [("Новая партия",self.setup),("Выбрать бой",self.catalog),("Практика",self.drills),("Настройки",self.settings),("Выход",self.close)]:
            button(menu,title,action,action==self.setup).pack(fill="x",pady=4)

        audio=tk.Frame(page,bg=CARD,padx=12,pady=9,highlightbackground="#493660",highlightthickness=1)
        audio.place(relx=1,x=-16,y=16,anchor="ne")
        def update_audio(*_):
            self.music.configure(self.music_enabled.get(),self.music_volume.get())
            toggle.configure(text="Музыка  ·  Вкл." if self.music_enabled.get() else "Музыка  ·  Выкл.",
                             fg=MINT if self.music_enabled.get() else MUTED)
            slider.set_muted(not self.music_enabled.get())
        def toggle_audio():
            self.music_enabled.set(not self.music_enabled.get())
            update_audio()
        toggle=button(audio,"Музыка  ·  Вкл." if self.music_enabled.get() else "Музыка  ·  Выкл.",toggle_audio)
        toggle.configure(fg=MINT if self.music_enabled.get() else MUTED)
        toggle.pack(fill="x")
        slider=VolumeSlider(audio,self.music_volume,update_audio,muted=not self.music_enabled.get())
        slider.pack(fill="x",pady=(6,0))

    def settings(self):
        page=self.page("Настройки")
        self.nav.add_command(label="Главное меню",command=self.home)
        self.menu_backdrop(page)
        card=tk.Frame(page,bg=CARD,padx=22,pady=16,highlightbackground="#493660",highlightthickness=1)
        card.place(relx=.5,rely=.5,relwidth=.89,anchor="center")

        label(card,"Настройки",25,PAPER,True).pack(pady=(0,9))
        section_color="#231e33"
        timing=tk.Frame(card,bg=section_color,padx=11,pady=9)
        timing.pack(fill="x")
        label(timing,"Частота случайных испытаний",11,MINT,True).pack(anchor="w",pady=(0,5))
        option_picker(timing,self.rate,RATES,6).pack(fill="x")

        options=tk.Frame(card,bg=CARD)
        options.pack(fill="x",pady=(10,8))
        for col,title,rows in [
            (0,"Игра и интерфейс",[
                ("QTE при взятии",self.qte),
                ("Лабиринт «Контур» в случайных QTE",self.circuit),
                ("Ускорение с Shift",self.sprint),
                ("Анимация фона меню",self.motion),
            ]),
            (1,"Варианты совместных QTE",list(zip(
                ("Стекольщик","Маятник","Поперечный поток","Дрейф","Войти в круг","Покинуть круг"),
                self.variants))),
        ]:
            options.columnconfigure(col,weight=1,uniform="settings")
            group=tk.Frame(options,bg=section_color,padx=9,pady=8)
            group.grid(row=0,column=col,sticky="nsew",padx=(0,5) if col==0 else (5,0))
            label(group,title,11,MINT,True).pack(anchor="w",pady=(0,5))
            for text,var in rows:
                NeonCheck(group,text,var).pack(fill="x",pady=1)

        notes=tk.Frame(card,bg=section_color,padx=10,pady=7)
        notes.pack(fill="x")
        for hint in (
            "Ускорение с инерцией. Вдвоём: белые — WASD и левый Shift, чёрные — стрелки и правый Shift.",
            "Край арены отнимает сердце. Победа в лабиринте даёт два сердца, максимум — пять.",
        ):
            label(notes,hint,9,MUTED).pack(anchor="w")
        button(card,"Сохранить и вернуться",self.save_settings,True).pack(pady=(10,0))

    def save_settings(self):
        if not any(v.get() for v in self.variants):
            self.alert("Варианты QTE","Выберите хотя бы одно испытание.")
            return
        self.config_path.parent.mkdir(parents=True,exist_ok=True)
        self.config_path.write_text(json.dumps(dict(rate=self.rate.get(),capture=self.qte.get(),maze=self.circuit.get(),motion=self.motion.get(),sprint=self.sprint.get(),variants=[i for i,v in enumerate(self.variants) if v.get()])),encoding="utf8")
        self.home()

    def retry_toggle(self,page,command=None):
        tk.Checkbutton(page,text="Авторетрай после поражения",variable=self.retry,command=command,
                       bg=page.cget("bg"),fg=PAPER,selectcolor=INK,activebackground=page.cget("bg"),
                       activeforeground=MINT,font=("Segoe UI",11)).pack(anchor="center",pady=8)

    def drills(self):
        page=self.page("Практика")
        self.nav.add_command(label="Главное меню",command=self.home)
        label(page,"Практика QTE",24,PAPER,True).pack(anchor="center")
        text_block(page,"Стрелки или WASD · Shift для ускорения",11,MINT).pack(anchor="center",pady=8)
        self.retry_toggle(page)
        names=("Стекольщик","Маятник","Поперечный поток","Дрейф","Войти в круг","Покинуть круг","Контур")
        grid=tk.Frame(page,bg=CARD)
        grid.pack(fill="x")
        for i,name in enumerate(names):
            grid.columnconfigure(i%3,weight=1,uniform="drills")
            button(grid,name,lambda k=i,n=name:self.run_drill(k,n)).grid(
                row=i//3,column=i%3,sticky="ew",padx=3,pady=3)
        button(page,"← Главное меню",self.home).pack(anchor="center",pady=14)

    def run_drill(self,key,name):
        page=self.page("Практика")
        self.nav.add_command(label="Практика",command=self.drills)
        if key not in (4,5):
            label(page,name,20,PAPER,True).pack(anchor="center")
        field=tk.Frame(page,bg=INK)
        field.pack(fill="both",expand=True,pady=8)
        button(page,"← К списку испытаний",self.drills).pack(anchor="center")
        if key<2:
            Arena(field,dict(kind="arena",boss=key,sprint=self.sprint.get(),seed=random.randrange(1000000)),
                  lambda ok:self.drill_result(key,name,ok))
            return
        view=DuelView(field,"practice")
        view.sprint=self.sprint.get()
        view.buffer_turns=key==6
        model=Circuit() if key==6 else Survival(random.randrange(1000000),True,practice=True)
        if key!=6:
            model.pattern=key
        previous=time.monotonic()
        def tick():
            nonlocal previous
            self.drill_job=None
            now=time.monotonic()
            dt=now-previous
            directions=(model.bot(),view.direction(True))
            outcome=(model.step(min(.055,dt),directions,clock_dt=dt) if key!=6
                     else model.step(min(.055,dt),directions))
            previous=now
            if key==6 and outcome:
                self.drill_result(key,name,model.scores[1]>model.scores[0])
            elif key!=6 and (1 in outcome or model.complete or (key<4 and model.elapsed>=15)):
                self.drill_result(key,name,1 not in outcome)
            else:
                view.paint(model.snapshot())
                self.drill_job=self.root.after(16 if key==6 else 30,tick)
        self.drill_job=self.root.after(16 if key==6 else 30,tick)

    def drill_result(self,key,name,success):
        page=self.page("Результат")
        self.nav.add_command(label="Практика",command=self.drills)
        card=tk.Frame(page,bg="#26213b",padx=36,pady=28,highlightthickness=1,
                      highlightbackground="#493660")
        card.place(relx=.5,rely=.5,anchor="center")
        label(card,name,28,PAPER,True).pack(pady=(0,8))
        status=text_block(card,"Победа" if success else "Поражение",14,MINT if success else GOLD)
        status.pack(anchor="center",pady=10)
        restart=lambda:self.run_drill(key,name)
        button(card,"Играть снова",restart,True).pack(fill="x",pady=(4,8))
        def toggle():
            if self.drill_job is not None:
                self.root.after_cancel(self.drill_job)
                self.drill_job=None
            automatic=not success and self.retry.get()
            status.configure(text="Победа" if success else "Поражение · повтор через секунду" if automatic else "Поражение")
            if automatic:
                self.drill_job=self.root.after(1000,restart)
        self.retry_toggle(card,toggle)
        button(card,"← К списку испытаний",self.drills).pack(fill="x")
        toggle()

    def catalog(self, note=""):
        page=self.page("Выбор боя")
        self.nav.add_command(label="Главное меню",command=self.home)
        self.nav.add_command(label="Новая партия",command=self.setup)
        label(page,"Выбрать бой",24,PAPER,True).pack(anchor="center")
        if note:
            text_block(page,note,12,GOLD).pack(anchor="center")
        groups=[("Встроенные арены",[("Стекольщик",0),("Маятник",1)]),
                ("Undertale Boss Fight",[("Toriel","toriel"),("Papyrus","papyrus"),("Sans","sans"),
                 ("Asgore","asgore"),("Undyne","undyne"),("Undyne the Undying","undying"),
                 ("Muffet","muffet"),("Mettaton EX","ex"),("Mettaton NEO","neo"),("Asriel","asriel")])]
        for heading,items in groups:
            label(page,heading,12,MINT,True).pack(anchor="center",pady=(6,3))
            grid=tk.Frame(page,bg=CARD)
            grid.pack(fill="x")
            for i,(name,key) in enumerate(items):
                grid.columnconfigure(i%3,weight=1,uniform="tiles")
                button(grid,name,lambda k=key,n=name:self.practice(k,n)).grid(row=i//3,column=i%3,sticky="ew",padx=3,pady=3)
        button(page,"← Главное меню",self.home).pack(anchor="center",pady=14)

    def practice(self,key,name):
        page=self.page("Бой")
        self.nav.add_command(label="Выбор боя",command=self.leave_catalog_fight)
        if isinstance(key,int):
            self.arena=Arena(page,dict(kind="arena",boss=key,sprint=self.sprint.get(),seed=random.randrange(1000000)),self.practice_done)
            return
        project=self.external_path or self.encounter_path
        try:
            if not (project/"build/classes/java/main/Main.class").is_file():
                raise OSError("Сначала подключите сборку Undertale Boss Fight в настройках партии.")
            self.proc,self.encounter_dir=launch(self.java(),project,0,key)
            self.training=True
            label(page,name,24,PAPER,True).pack(anchor="center")
            label(page,"Бой открыт в отдельном окне.",12,MINT).pack(anchor="center")
        except OSError as exc:
            self.catalog(str(exc))

    def leave_catalog_fight(self):
        self.stop_encounter()
        self.proc=None
        self.training=False
        self.clear_event()
        self.catalog()

    def practice_done(self,success):
        self.training=False
        self.clear_event()
        self.catalog("Победа" if success else "Бой завершён")

    def clean(self):
        for child in self.side.winfo_children():
            child.destroy()

    def section(self,text):
        label(self.side,text,9,MUTED,True).pack(anchor="center",pady=(6,3))

    def setup(self):
        self.nav.screen("Новая партия")
        self.nav.add_command(label="Главное меню",command=self.home)
        if self.menu_page:
            self.menu_page.destroy()
            self.menu_page=None
        self.clean()
        button(self.side,"← Главное меню",self.home).pack(side="bottom",fill="x",pady=2)
        label(self.side,"Новая партия",20,PAPER,True).pack(anchor="center")
        self.section("РЕЖИМ ИГРЫ")
        for name in MODES:
            tk.Radiobutton(self.side,text=name,variable=self.mode,value=name,command=self.setup,indicatoron=False,
                           bg=LINE,fg=PAPER,selectcolor="#68316e",activebackground="#4f4167",
                           activeforeground=PAPER,relief="flat",bd=0,anchor="center",padx=10,pady=2,
                           cursor="hand2",font=("Segoe UI",10)).pack(fill="x",pady=1)
        if self.mode.get()==MODES[0]:
            self.section("СЛОЖНОСТЬ · STOCKFISH 19")
            option_picker(self.side,self.level,LEVELS,2).pack(fill="x")
        self.section("ЧАСТОТА БОЁВ")
        option_picker(self.side,self.rate,RATES,3).pack(fill="x")
        tk.Checkbutton(self.side,text="QTE при взятии",variable=self.qte,bg=CARD,fg=PAPER,
                       selectcolor=INK,activebackground=CARD,activeforeground=MINT,font=("Segoe UI",11)).pack(anchor="center",pady=(6,2))
        button(self.side,"Сменить арены…" if self.external_path else "Арены: встроенные  ▾",self.pick_external).pack(fill="x")
        button(self.side,"Начать партию   →",self.start,True).pack(side="bottom",fill="x")
        self.draw()

    def pick_external(self):
        if self.external_path and self.ask("Арены","Переключиться на встроенные арены?"):
            self.external_path = None
        else:
            folder = filedialog.askdirectory(title="Папка собранного undertale-boss-fight (gradlew classes)")
            if not folder: return
            path = Path(folder)
            if not (path/"build/classes/java/main/Main.class").is_file() or not self.java():
                self.alert("Undertale Boss Fight","Нужны Java в PATH и папка проекта после gradlew.bat classes. Подробности в README.")
                return
            self.external_path = path
        self.setup()

    @staticmethod
    def java():
        home = Path(os.environ.get("JAVA_HOME","."))/"bin/javaw.exe"
        return str(home) if home.is_file() else shutil.which("javaw") or shutil.which("java") or str(Path(os.environ["APPDATA"])/"PrismLauncher/java/java-runtime-delta/bin/javaw.exe")

    def start(self):
        self.nav.screen("Подключение")
        self.role = ["bot","local","host","guest"][MODES.index(self.mode.get())]
        if self.role in ("host","guest"):
            address = None
            if self.role == "guest":
                address = self.prompt("Вход по LAN","IPv4-адрес создателя стола:",parent=self.root)
                if not address or not address.strip():
                    self.role = None
                    self.setup()
                    return
                address = address.strip()
            self.link = Link()
            self.link.start(address)
            self.clean()
            label(self.side,"Сетевой стол",19,PAPER,True).pack(anchor="center")
            self.info = label(self.side,"Подключение…",11,MINT)
            self.info.configure(wraplength=225)
            self.info.pack(anchor="center",pady=12)
            button(self.side,"Отмена",self.reset).pack(side="bottom",fill="x")
        else:
            self.begin(bool(self.external_path))

    def begin(self,external):
        self.game = Match(RATES[self.rate.get()],self.qte.get(),external)
        self.schedule()
        self.publish()

    def schedule(self):
        lo,hi = self.game.interval
        self.deadline = time.monotonic()+random.uniform(lo,hi) if hi else float("inf")

    def mine(self):
        return self.role == "local" or self.board.turn == (self.role != "guest")

    def publish(self):
        if self.game.event:
            event=self.game.event
            event["sprint"]=self.sprint.get()
            if event["kind"] in ("duel","arena") and "pattern" not in event:
                event["pattern"]=random.Random(event["seed"]).choice([i for i,v in enumerate(self.variants) if v.get()] or [0])
        state = self.game.state()
        if self.role == "host":
            self.link.outbox.put(dict(type="state",data=state))
        self.show(state)

    def show(self,state):
        old_hp = self.state["hp"] if self.state else None
        self.state = state
        self.board = chess.Board(state["fen"])
        self.nav.screen("Партия")
        sender=self.board.turn if self.role=="local" else self.role!="guest"
        for kind,title in [("energy","Предложить бой за энергию"),("undo","Попросить вернуть свой ход"),("draw","Предложить ничью"),("resign","Сдаться")]:
            enabled=not state["result"] and not state["event"]
            if kind=="undo":
                enabled=enabled and len(state["history"]) >= (2 if self.board.turn==sender else 1)
            self.nav.add_command(label=title,state="normal" if enabled else "disabled",
                                 command=lambda k=kind:self.table_action(k))
        self.nav.add_separator()
        self.nav.add_command(label="Главное меню",command=self.leave)
        self.selected = None
        self.clean()
        label(self.side,self.mode.get(),10,MINT,True).pack(anchor="center")
        title = state["result"] or ("Ход белых" if self.board.turn else "Ход чёрных")
        label(self.side,title,19,PAPER,True).pack(anchor="center")
        if state["notice"]:
            text_block(self.side,state["notice"],9,MINT,width=195).pack(anchor="center")
        if self.board.is_check(): label(self.side,"Шах",12,GOLD,True).pack(anchor="center")
        self.section("СЕРДЦА")
        for side,name in [(1,"Белые"),(0,"Чёрные")]:
            hp = state["hp"][side]
            hearts(self.side,name,hp)
        self.section("ПОСЛЕДНИЕ ХОДЫ")
        hist = text_block(self.side,"   ".join(state["history"]) or "Пока ходов нет",11,width=195)
        hist.configure(wraplength=195)
        hist.pack(anchor="center")
        self.section("ПАРАМЕТРЫ СТОЛА")
        lo,hi = state["interval"]
        label(self.side,("Бой каждые %s–%s с" % (lo,hi)) if hi else "Бои выключены",10,MUTED).pack(anchor="center")
        label(self.side,"QTE "+("включены" if state["qte"] else "выключены"),10,MUTED).pack(anchor="center")
        if hi:
            label(self.side,"Арены: "+("Undertale" if state["external"] else "встроенные"),10,MUTED).pack(anchor="center")
        sender = not self.board.turn if self.role=="local" else self.role!="guest"
        if not state["result"] and not state["event"] and sender!=self.board.turn and state["charges"][sender]:
            ready=time.monotonic()+state["delay"][sender]
            def challenge():
                if time.monotonic()<ready:
                    self.alert("Перерыв",f"До вызова: {int(ready-time.monotonic())+1} с")
                elif self.role=="guest":
                    self.link.outbox.put(dict(type="throw",fen=state["fen"]))
                elif self.game.throw(sender):
                    self.publish()
            button(self.side,"Бросить QTE · %d/3"%state["charges"][sender],challenge).pack(fill="x")
        if state["claim"] and self.mine():
            button(self.side,"Потребовать ничью",self.claim).pack(fill="x",pady=4)
        if old_hp and any(after < before for before,after in zip(old_hp,state["hp"])):
            label(self.side,"Промах · −1 энергия",11,GOLD,True).pack(anchor="center",pady=8)
        button(self.side,"Вернуться в меню",self.leave).pack(side="bottom",fill="x")
        self.upper.configure(text="○   Белые" if self.role=="guest" else "●   Чёрные")
        self.lower.configure(text="●   Чёрные" if self.role=="guest" else "○   Белые")
        self.draw()
        event = state["event"]
        if not event or state["result"]:
            self.clear_event()
        elif self.active_event != event["id"]:
            self.clear_event()
            self.active_event = event["id"]
            if event["kind"]=="offer":
                frame=tk.Frame(self.surface,bg=CARD,padx=16,pady=15)
                self.arena=frame
                frame.place(relx=.5,rely=.5,anchor="center")
                who="Белые" if event["sender"] else "Чёрные"
                text=" предлагают ничью" if event["action"]=="draw" else " просят вернуть свой ход"
                if event["action"]=="energy": text=" предлагают бой за энергию"
                label(frame,who+text,14,MINT,True).pack()
                if self.role=="local" or (self.role=="host" and not event["sender"]) or (self.role=="guest" and event["sender"]):
                    for ok,title in [(True,"Принять"),(False,"Отклонить")]:
                        button(frame,title,lambda v=ok:self.answer_offer(v),ok).pack(side="left",padx=4,pady=8)
                else:
                    label(frame,"Ожидание ответа соперника",11).pack()
            elif event["kind"] in ("survival","duel","arena","maze"):
                self.arena=DuelView(self.surface,self.role)
                self.maze_active=event["kind"]=="maze"
                self.arena.buffer_turns=self.maze_active
                self.remote_turn=None
                self.duel=Circuit() if event["kind"]=="maze" else Survival(event["seed"],event["kind"]!="survival")
                self.remote_dir=(0,0,0)
                if "pattern" in event:self.duel.pattern=event["pattern"]
                self.arena.sprint=event.get("sprint",True)
                self.duel_ready=self.role!="host"
                self.duel_time=time.monotonic()
                self.last_dir=None
                if self.role=="guest":
                    self.link.outbox.put(dict(type="duel_ready",id=event["id"]))
                self.arena.paint(self.duel.snapshot())
            elif self.mine() or (self.role=="bot" and event["kind"]=="mate"):
                if event["kind"] in ("external","mate"):
                    self.launch_external()
                else:
                    self.arena = Arena(self.surface,dict(event,kind="arena"),self.finish)
            else:
                self.wait_overlay("Соперник проходит испытание за взятие" if event["kind"]=="qte" else "Соперник проходит испытание")
        self.bot_at = time.monotonic()+.85
        if self.premove:
            move,ply=self.premove
            current=self.board.ply()
            if state["result"] or current not in (ply,ply+1):
                self.cancel_premove()
            elif self.mine() and not state["event"]:
                self.cancel_premove()
                if current==ply+1 and self.board.is_legal(move):
                    self.send_move(move)

    def cancel_premove(self,event=None):
        self.premove=None
        self.selected=None
        self.draw()

    def send_move(self,move):
        if self.role=="guest":
            self.link.outbox.put(dict(type="move",uci=move.uci(),fen=self.state["fen"]))
        elif self.game.move(move.uci()):
            self.publish()

    def table_action(self,kind):
        state=self.state
        if not state or state["result"] or state["event"]: return
        sender=self.board.turn if self.role=="local" else self.role!="guest"
        if kind=="resign" and not self.ask("Сдаться?","Засчитать победу сопернику?"): return
        if self.state is not state: return
        if self.role=="guest":
            self.link.outbox.put(dict(type="action",kind=kind,fen=state["fen"]))
        elif self.game.action(sender,kind):
            self.search=None
            self.publish()

    def answer_offer(self,accepted):
        event=self.state["event"]
        if self.role=="guest":
            self.link.outbox.put(dict(type="reply",id=event["id"],ok=accepted))
        elif self.game.reply(not event["sender"],event["id"],accepted):
            self.search=None
            self.schedule()
            self.publish()

    def wait_overlay(self,text):
        self.arena = tk.Label(self.surface,text=text,font=("Segoe UI",15,"bold"),bg=CARD,fg=MINT,pady=22)
        self.arena.place(relx=.5,rely=.5,relwidth=1,anchor="center")

    def launch_external(self):
        try:
            self.proc,self.encounter_dir = launch(self.java(),self.external_path or self.encounter_path,self.state["event"]["seed"])
            self.wait_overlay("Идёт бой в отдельном окне")
        except (OSError,TypeError) as exc:
            self.alert("Запуск боя",str(exc))
            self.root.after_idle(lambda: self.finish(self.state["event"]["kind"]!="mate") if self.active_event else None)

    def clear_event(self):
        self.duel=None
        self.maze_active=False
        if self.arena:
            self.arena.destroy()
            self.arena = None
        self.active_event = None

    def claim(self):
        if self.role == "guest":
            self.link.outbox.put(dict(type="claim",fen=self.state["fen"]))
        elif self.game.claim():
            self.publish()

    def finish(self,success):
        ident = self.active_event
        if ident is None: return
        self.clear_event()
        if self.role=="guest":
            self.link.outbox.put(dict(type="finish",id=ident,ok=success))
        elif self.game.finish(ident,success):
            self.schedule()
            self.publish()

    def square(self,col,row):
        if self.role=="guest":
            return chess.square(7-col,row)
        return chess.square(col,7-row)

    def highlighted_moves(self):
        if self.selected is None:
            return set()
        board=self.board
        if not self.mine():
            board=board.copy(stack=False)
            board.turn=self.role!="guest"
            board.ep_square=None
        return {move.to_square for move in board.generate_legal_moves(
            from_mask=chess.BB_SQUARES[self.selected])}

    def draw(self):
        c = self.canvas
        w,h = c.winfo_width(),c.winfo_height()
        cell = max(1,min((w-30)//8,(h-25)//8))
        x0,y0 = (w-cell*8)//2+5,(h-cell*8)//2-5
        self.geometry = x0,y0,cell
        c.delete("all")
        last = self.state["last"] if self.state else ""
        legal = self.highlighted_moves()
        for row in range(8):
            for col in range(8):
                sq = self.square(col,row)
                x,y = x0+col*cell,y0+row*cell
                light = (row+col)%2==0
                color = "#b4abc9" if light else "#62577f"
                if last and chess.square_name(sq) in (last[:2],last[2:4]):
                    color = "#d9d89d" if light else "#a4b982"
                if self.premove and sq in (self.premove[0].from_square,self.premove[0].to_square):color="#aa65c7"
                if sq==self.selected: color=GOLD
                c.create_rectangle(x,y,x+cell,y+cell,fill=color,outline="")
                p = self.board.piece_at(sq)
                if p:
                    self.pieces.draw(x,y,cell,p)
                if sq in legal:
                    radius = cell*(.43 if p else .095)
                    cx,cy=x+cell/2,y+cell/2
                    c.create_oval(cx-radius,cy-radius,cx+radius,cy+radius,outline="#315b4b",width=3,fill="" if p else "#315b4b")
                if row==7: c.create_text(x+cell/2,y+cell+10,text=chess.FILE_NAMES[chess.square_file(sq)],fill=MUTED)
                if col==0: c.create_text(x-10,y+cell/2,text=chess.square_rank(sq)+1,fill=MUTED)

    def click(self,e):
        if not self.state or self.state["result"] or self.state["event"] : return
        x,y,cell = self.geometry
        col,row=(e.x-x)//cell,(e.y-y)//cell
        if not (0<=col<8 and 0<=row<8): return
        sq = self.square(col,row)
        if not self.mine():
            own=self.role!="guest"
            target=self.board.piece_at(sq)
            if self.selected is None or sq==self.selected:
                self.selected=sq if target and target.color==own and sq!=self.selected else None
            else:
                source=self.board.piece_at(self.selected)
                promote=None
                if source and source.piece_type==chess.PAWN and chess.square_rank(sq) in (0,7):
                    position=self.state
                    choice=self.prompt("Превращение","Выбери q, r, b или n",initialvalue="q")
                    if position is not self.state or not choice or choice.lower() not in ("q","r","b","n"):return
                    promote=chess.PIECE_SYMBOLS.index(choice.lower())
                self.premove=(chess.Move(self.selected,sq,promotion=promote),self.board.ply())
                self.selected=None
            self.draw()
            return
        moves = [m for m in self.board.legal_moves if m.from_square==self.selected and m.to_square==sq]
        if moves:
            move=moves[0]
            if move.promotion:
                choice=self.prompt("Превращение","Ферзь (q), ладья (r), слон (b) или конь (n):",initialvalue="q")
                move=next((m for m in moves if chess.piece_symbol(m.promotion)==(choice or "").strip().lower()),None)
                if not move or self.state["event"]: return
            self.send_move(move)
        else:
            piece=self.board.piece_at(sq)
            self.selected=sq if piece and piece.color==self.board.turn and sq!=self.selected else None
            self.draw()

    def network(self,kind,data):
        if kind=="listening":
            ips=socket.gethostbyname_ex(socket.gethostname())[2]
            self.info.configure(text="Ожидание друга\n\nIPv4: "+", ".join(ips)+"\nTCP "+str(PORT))
        elif kind=="connected" and self.role=="guest":
            self.link.outbox.put(dict(type="ready",external=bool(self.external_path)))
        elif kind=="message":
            typ=data.get("type")
            if self.duel and data.get("id")==self.active_event:
                if self.role=="host" and typ=="duel_ready":
                    self.duel_ready=True
                    self.duel_time=time.monotonic()
                elif self.role=="host" and typ=="direction":
                    pair=data.get("xy")
                    if isinstance(pair,list) and len(pair)==3 and all(type(x) is int and abs(x)<=1 for x in pair):
                        self.remote_dir=pair
                        if self.maze_active and any(pair[:2]):
                            self.remote_turn=pair
                elif self.role=="guest" and typ=="frame":
                    self.arena.paint(data["frame"])
            if self.role=="host":
                if typ=="ready" and not self.game:
                    self.begin(bool(self.external_path and data.get("external") is True))
                elif typ=="action" and self.game and data.get("fen")==self.game.board.fen() and self.game.action(False,data.get("kind")):
                    self.publish()
                elif typ=="reply" and self.game and type(data.get("ok")) is bool and self.game.reply(False,data.get("id"),data["ok"]):
                    self.schedule()
                    self.publish()
                elif typ=="throw" and self.game and data.get("fen")==self.game.board.fen() and self.game.throw(False):
                    self.publish()
                elif self.game and not self.game.board.turn:
                    if typ=="move" and data.get("fen")==self.game.board.fen() and self.game.move(data.get("uci")):
                        self.publish()
                    elif typ=="claim" and data.get("fen")==self.game.board.fen() and self.game.claim():
                        self.publish()
                    elif typ=="finish" and type(data.get("ok")) is bool and self.game.finish(data.get("id"),data["ok"]):
                        self.schedule()
                        self.publish()
            elif typ=="state": self.show(data["data"])
        elif kind=="error":
            self.reset()
            self.alert("Сетевой стол",data)

    def poll(self):
        try:
            self.music.tick(external=self.proc is not None)
            while self.link:
                try: kind,data=self.link.events.get_nowait()
                except queue.Empty: break
                self.network(kind,data)
            now=time.monotonic()
            if self.proc and self.proc.poll() is not None:
                code=self.proc.returncode
                self.proc=None
                self.encounter_dir.cleanup()
                self.encounter_dir=None
                if code not in (0,10,11):
                    self.alert("Undertale Boss Fight","Процесс завершился с кодом %d. Проверьте сборку и ресурсы. Энергия сохранена." % code)
                if self.training:
                    self.practice_done(code==10)
                    return
                self.finish(code==10 if self.state["event"]["kind"]=="mate" else code not in (0,11))
            if self.role=="guest" and self.duel:
                direction=self.arena.direction(False)
                if direction!=self.last_dir:
                    self.link.outbox.put(dict(type="direction",id=self.active_event,xy=direction))
                    self.last_dir=direction
            g=self.game
            if g and not g.result:
                if self.duel:
                    if self.duel_ready:
                        black=self.remote_dir if self.role=="host" else self.duel.bot() if self.role=="bot" else self.arena.direction(False)
                        dt=now-self.duel_time
                        if self.role=="host" and self.maze_active and self.remote_turn:
                            black=self.remote_turn
                            self.remote_turn=None
                        directions=(black,self.arena.direction(True))
                        dead=(self.duel.step(min(.075,dt),directions,clock_dt=dt) if isinstance(self.duel,Survival)
                              else self.duel.step(min(.075,dt),directions))
                        self.duel_time=now
                        if dead or (isinstance(self.duel,Survival) and self.duel.complete):
                            if isinstance(self.duel,Circuit): g.end_circuit(self.duel.scores)
                            else: g.end_survival(dead)
                            self.schedule()
                            self.publish()
                        else:
                            frame=self.duel.snapshot()
                            self.arena.paint(frame)
                            if self.role=="host":
                                self.link.outbox.put(dict(type="frame",id=self.active_event,frame=frame))
                elif g.event and g.event["kind"]=="offer":
                    if self.role=="bot" and now>=self.bot_at:
                        self.answer_offer(True)
                elif not g.event and now>=self.deadline:
                    g.challenge("maze" if self.circuit.get() and random.randrange(3)==0 else "external" if g.external and random.randrange(2)==0 else "arena")
                    self.publish()
                elif self.role=="bot" and not g.board.turn and now>=self.bot_at and not (g.event and g.event["kind"]=="mate"):
                    if g.event: self.finish(random.random()<.82)
                    else:
                        if self.search is None:
                            self.search=self.worker.submit(computer_move,g.board.copy(),self.level.get())
                        elif self.search.done():
                            move=self.search.result()
                            self.search=None
                            if g.move(move):
                                self.publish()
        except (chess.engine.EngineError,TimeoutError,KeyError,ValueError,TypeError,IndexError,AttributeError,OSError) as exc:
            self.reset()
            self.alert("Ошибка партии",str(exc))
        finally:
            self.root.after(20 if self.maze_active else 50,self.poll)

    def leave(self):
        if self.state["result"] or self.ask("Завершить партию?","Вернуться к настройкам и закрыть текущую партию?"):
            self.reset()

    def reset(self):
        self.premove=None
        self.search=None
        if self.link: self.link.close()
        self.stop_encounter()
        self.link=self.proc=self.game=self.state=self.selected=self.role=None
        self.clear_event()
        self.board=chess.Board()
        self.upper.configure(text="●   Чёрные")
        self.lower.configure(text="○   Белые")
        self.draw()
        self.home()

    def stop_encounter(self):
        if self.proc and self.proc.poll() is None: self.proc.terminate()
        if self.proc: self.proc.wait()
        if self.encounter_dir:
            self.encounter_dir.cleanup()
            self.encounter_dir=None

    def close(self):
        self.music.close()
        self.worker.shutdown(wait=False,cancel_futures=True)
        if self.link: self.link.close()
        self.stop_encounter()
        self.root.destroy()


if __name__=="__main__":
    App(tk.Tk()).root.mainloop()
