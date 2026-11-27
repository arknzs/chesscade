import os
import queue
import random
import shutil
import socket
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import chess
import chess.engine
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
from match import Match, MAX_ENERGY

CARD, MUTED, LINE = "#20312f", "#afc1b5", "#39504a"
MODES = ["С компьютером", "Вдвоём за доской", "Создать LAN-стол", "Войти по IP"]
RATES = {"Редко": (65,110), "Обычно": (30,65), "Часто": (10,24), "Выкл.": (0,0)}


def label(parent, text, size=11, color=PAPER, bold=False):
    return tk.Label(parent, text=text, fg=color, bg=parent.cget("bg"), anchor="w",
                    justify="left", font=("Segoe UI",size,"bold" if bold else "normal"))


def button(parent, text, command, primary=False):
    return tk.Button(parent, text=text, command=command, relief="flat", bd=0,
                     bg=MINT if primary else LINE, fg=INK if primary else PAPER,
                     activebackground=GOLD, activeforeground=INK, cursor="hand2",
                     padx=12, pady=7, font=("Segoe UI",10,"bold"))


class App:
    def __init__(self, root):
        self.root = root
        root.title("Гамбит 67")
        root.iconbitmap(str(Path(__file__).with_name("gambit.ico")))
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
        self.external_path = None
        self.link = self.game = self.state = self.arena = self.proc = None
        self.encounter_dir = None
        self.active_event = self.selected = None
        self.board = chess.Board()
        self.deadline = self.bot_at = float("inf")
        self.banner = tk.Frame(root,bg=INK)
        self.banner.pack(fill="x",padx=26,pady=(17,12))
        label(self.banner,"◈",23,MINT,True).pack(side="left")
        label(self.banner,"  ГАМБИТ 67",18,PAPER,True).pack(side="left")
        label(self.banner,"ШАХМАТЫ   /   АРКАДА",9,MUTED,True).pack(side="right")
        self.menu_page = None
        self.training = False
        self.body = body = tk.Frame(root,bg=INK)
        body.pack(fill="both",expand=True,padx=24,pady=(0,20))
        self.side = tk.Frame(body,bg=CARD,width=265,padx=17,pady=14)
        self.side.pack(side="right",fill="y",padx=(14,0))
        self.side.pack_propagate(False)
        self.play = tk.Frame(body,bg=INK)
        self.play.pack(side="left",fill="both",expand=True)
        self.upper = label(self.play,"●   Чёрные",12,MUTED,True)
        self.upper.pack(anchor="w",pady=(1,4))
        self.surface = tk.Frame(self.play,bg=INK)
        self.surface.pack(fill="both",expand=True)
        self.canvas = tk.Canvas(self.surface,bg=INK,highlightthickness=0)
        self.canvas.pack(fill="both",expand=True)
        self.canvas.bind("<Configure>",lambda _: self.draw())
        self.canvas.bind("<Button-1>",self.click)
        self.lower = label(self.play,"○   Белые",12,PAPER,True)
        self.lower.pack(anchor="w",pady=(4,0))
        self.home()
        root.protocol("WM_DELETE_WINDOW",self.close)
        root.after(50,self.poll)

    def page(self):
        if self.menu_page:
            self.menu_page.destroy()
        self.menu_page=tk.Frame(self.body,bg=CARD,padx=40,pady=28)
        self.menu_page.place(relwidth=1,relheight=1)
        return self.menu_page

    def home(self):
        page=self.page()
        label(page,"Главное меню",28,PAPER,True).pack(anchor="w",pady=(30,24))
        for title,action in [("Новая партия",self.setup),("Выбрать бой",self.catalog),("Выход",self.close)]:
            button(page,title,action,action==self.setup).pack(anchor="w",ipadx=30,pady=5)

    def catalog(self, note=""):
        page=self.page()
        label(page,"Выбрать бой",24,PAPER,True).pack(anchor="w")
        if note:
            label(page,note,12,GOLD).pack(anchor="w")
        groups=[("Встроенные арены",[("Стекольщик",0),("Маятник",1)]),
                ("Undertale Boss Fight",[("Toriel","toriel"),("Papyrus","papyrus"),("Sans","sans"),
                 ("Asgore","asgore"),("Undyne","undyne"),("Undyne the Undying","undying"),
                 ("Muffet","muffet"),("Mettaton EX","ex"),("Mettaton NEO","neo"),("Asriel","asriel")])]
        for heading,items in groups:
            label(page,heading,12,MINT,True).pack(anchor="w",pady=(12,4))
            grid=tk.Frame(page,bg=CARD)
            grid.pack(fill="x")
            for i,(name,key) in enumerate(items):
                grid.columnconfigure(i%3,weight=1,uniform="tiles")
                button(grid,name,lambda k=key,n=name:self.practice(k,n)).grid(row=i//3,column=i%3,sticky="ew",padx=3,pady=3)
        button(page,"← Главное меню",self.home).pack(anchor="w",pady=14)

    def practice(self,key,name):
        page=self.page()
        if isinstance(key,int):
            self.arena=Arena(page,dict(kind="arena",boss=key,seed=random.randrange(1000000)),self.practice_done)
            return
        project=self.external_path or Path(os.environ["LOCALAPPDATA"])/"Gambit67Encounters"
        try:
            if not (project/"build/classes/java/main/Main.class").is_file():
                raise OSError("Сначала подключите сборку Undertale Boss Fight в настройках партии.")
            self.proc,self.encounter_dir=launch(self.java(),project,0,key)
            self.training=True
            label(page,name,24,PAPER,True).pack(anchor="w")
            label(page,"Бой открыт в отдельном окне.",12,MINT).pack(anchor="w")
        except OSError as exc:
            self.catalog(str(exc))

    def practice_done(self,success):
        self.training=False
        self.clear_event()
        self.catalog("Победа" if success else "Бой завершён")

    def clean(self):
        for child in self.side.winfo_children():
            child.destroy()

    def section(self,text):
        label(self.side,text,9,MUTED,True).pack(anchor="w",pady=(12,4))

    def setup(self):
        if self.menu_page:
            self.menu_page.destroy()
            self.menu_page=None
        self.clean()
        button(self.side,"← Главное меню",self.home).pack(side="bottom",fill="x",pady=2)
        label(self.side,"Новая партия",20,PAPER,True).pack(anchor="w")
        self.section("РЕЖИМ ИГРЫ")
        for name in MODES:
            tk.Radiobutton(self.side,text=name,variable=self.mode,value=name,command=self.setup,indicatoron=False,
                           bg=LINE,fg=PAPER,selectcolor="#46735b",activebackground="#46735b",
                           activeforeground=PAPER,relief="flat",bd=0,anchor="w",padx=10,pady=4,
                           cursor="hand2",font=("Segoe UI",10)).pack(fill="x",pady=1)
        if self.mode.get()==MODES[0]:
            self.section("СЛОЖНОСТЬ · STOCKFISH 19")
            choice=tk.OptionMenu(self.side,self.level,*LEVELS)
            choice.configure(bg=LINE,fg=PAPER,highlightthickness=0,bd=0)
            choice.pack(fill="x")
        self.section("ЧАСТОТА БОЁВ")
        menu = tk.OptionMenu(self.side,self.rate,*RATES)
        menu.configure(bg=LINE,fg=PAPER,activebackground=LINE,activeforeground=MINT,highlightthickness=0,bd=0)
        menu.pack(fill="x")
        tk.Checkbutton(self.side,text="QTE при взятии",variable=self.qte,bg=CARD,fg=PAPER,
                       selectcolor=INK,activebackground=CARD,activeforeground=MINT,font=("Segoe UI",11)).pack(anchor="w",pady=(6,2))
        button(self.side,"Сменить арены…" if self.external_path else "Арены: встроенные  ▾",self.pick_external).pack(fill="x")
        button(self.side,"Начать партию   →",self.start,True).pack(side="bottom",fill="x")
        label(self.side,"За промах в QTE или на арене теряется энергия. Пять промахов — поражение.",10,MUTED).pack(anchor="w",pady=9)
        self.side.winfo_children()[-1].configure(wraplength=222)
        self.draw()

    def pick_external(self):
        if self.external_path and messagebox.askyesno("Арены","Переключиться на встроенные арены?"):
            self.external_path = None
        else:
            folder = filedialog.askdirectory(title="Папка собранного undertale-boss-fight (gradlew classes)")
            if not folder: return
            path = Path(folder)
            if not (path/"build/classes/java/main/Main.class").is_file() or not self.java():
                messagebox.showinfo("Undertale Boss Fight","Нужны Java в PATH и папка проекта после gradlew.bat classes. Подробности в README.")
                return
            self.external_path = path
        self.setup()

    @staticmethod
    def java():
        home = Path(os.environ.get("JAVA_HOME","."))/"bin/javaw.exe"
        return str(home) if home.is_file() else shutil.which("javaw") or shutil.which("java") or str(Path(os.environ["APPDATA"])/"PrismLauncher/java/java-runtime-delta/bin/javaw.exe")

    def start(self):
        self.role = ["bot","local","host","guest"][MODES.index(self.mode.get())]
        if self.role in ("host","guest"):
            address = None
            if self.role == "guest":
                address = simpledialog.askstring("Вход по LAN","IPv4-адрес создателя стола:",parent=self.root)
                if not address or not address.strip():
                    self.role = None
                    return
                address = address.strip()
            self.link = Link()
            self.link.start(address)
            self.clean()
            label(self.side,"Сетевой стол",19,PAPER,True).pack(anchor="w")
            self.info = label(self.side,"Подключение…",11,MINT)
            self.info.configure(wraplength=225)
            self.info.pack(anchor="w",pady=12)
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
        state = self.game.state()
        if self.role == "host":
            self.link.outbox.put(dict(type="state",data=state))
        self.show(state)

    def show(self,state):
        old_hp = self.state["hp"] if self.state else None
        self.state = state
        self.board = chess.Board(state["fen"])
        self.selected = None
        self.clean()
        label(self.side,self.mode.get(),10,MINT,True).pack(anchor="w")
        title = state["result"] or ("Ход белых" if self.board.turn else "Ход чёрных")
        label(self.side,title,19,PAPER,True).pack(anchor="w")
        if self.board.is_check(): label(self.side,"Шах",12,GOLD,True).pack(anchor="w")
        self.section("ЭНЕРГИЯ")
        for side,name in [(1,"Белые"),(0,"Чёрные")]:
            hp = state["hp"][side]
            label(self.side,name+"     "+"◆ "*hp+"◇ "*(MAX_ENERGY-hp),12,MINT if hp else GOLD).pack(anchor="w")
        self.section("ПОСЛЕДНИЕ ХОДЫ")
        hist = label(self.side,"   ".join(state["history"]) or "Пока ходов нет",11)
        hist.configure(wraplength=220)
        hist.pack(anchor="w")
        self.section("ПАРАМЕТРЫ СТОЛА")
        lo,hi = state["interval"]
        label(self.side,("Бой каждые %s–%s с" % (lo,hi)) if hi else "Бои выключены",10,MUTED).pack(anchor="w")
        label(self.side,"QTE "+("включены" if state["qte"] else "выключены"),10,MUTED).pack(anchor="w")
        if hi:
            label(self.side,"Арены: "+("Undertale" if state["external"] else "встроенные"),10,MUTED).pack(anchor="w")
        sender = not self.board.turn if self.role=="local" else self.role!="guest"
        if not state["result"] and not state["event"] and sender!=self.board.turn and state["charges"][sender]:
            ready=time.monotonic()+state["delay"][sender]
            def challenge():
                if time.monotonic()<ready:
                    messagebox.showinfo("Перерыв",f"До вызова: {int(ready-time.monotonic())+1} с")
                elif self.role=="guest":
                    self.link.outbox.put(dict(type="throw",fen=state["fen"]))
                elif self.game.throw(sender):
                    self.publish()
            button(self.side,"Бросить QTE · %d/3"%state["charges"][sender],challenge).pack(fill="x")
        if state["claim"] and self.mine():
            button(self.side,"Потребовать ничью",self.claim).pack(fill="x",pady=4)
        if old_hp and old_hp != state["hp"]:
            label(self.side,"Промах · −1 энергия",11,GOLD,True).pack(anchor="w",pady=8)
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
            if self.mine() or (self.role=="bot" and event["kind"]=="mate"):
                if event["kind"] in ("external","mate"):
                    self.launch_external()
                else:
                    self.arena = Arena(self.surface,event,self.finish)
            else:
                self.wait_overlay("Соперник проходит испытание")
        self.bot_at = time.monotonic()+.85

    def wait_overlay(self,text):
        self.arena = tk.Label(self.surface,text=text,font=("Segoe UI",15,"bold"),bg=CARD,fg=MINT,pady=22)
        self.arena.place(relx=0,rely=.5,relwidth=1,anchor="w")

    def launch_external(self):
        try:
            self.proc,self.encounter_dir = launch(self.java(),self.external_path or Path(os.environ["LOCALAPPDATA"])/"Gambit67Encounters",self.state["event"]["seed"])
            self.wait_overlay("Идёт бой в отдельном окне")
        except (OSError,TypeError) as exc:
            messagebox.showerror("Запуск боя",str(exc))
            self.root.after_idle(lambda: self.finish(self.state["event"]["kind"]!="mate") if self.active_event else None)

    def clear_event(self):
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

    def draw(self):
        c = self.canvas
        w,h = c.winfo_width(),c.winfo_height()
        cell = max(1,min((w-30)//8,(h-25)//8))
        x0,y0 = (w-cell*8)//2+5,(h-cell*8)//2-5
        self.geometry = x0,y0,cell
        c.delete("all")
        last = self.state["last"] if self.state else ""
        legal = {m.to_square for m in self.board.legal_moves if m.from_square==self.selected}
        for row in range(8):
            for col in range(8):
                sq = self.square(col,row)
                x,y = x0+col*cell,y0+row*cell
                light = (row+col)%2==0
                color = "#dbe3c9" if light else "#648779"
                if last and chess.square_name(sq) in (last[:2],last[2:4]):
                    color = "#d9d89d" if light else "#a4b982"
                if sq==self.selected: color=GOLD
                c.create_rectangle(x,y,x+cell,y+cell,fill=color,outline="")
                p = self.board.piece_at(sq)
                if p:
                    symbol = chess.Piece(p.piece_type,False).unicode_symbol()
                    size = -int(cell*.82)
                    if p.color:
                        for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                            c.create_text(x+cell/2+dx,y+cell/2+dy,text=symbol,font=("Segoe UI Symbol",size),fill="#35473e")
                    c.create_text(x+cell/2,y+cell/2,text=symbol,font=("Segoe UI Symbol",size),fill="#fff6de" if p.color else "#172e2c")
                if sq in legal:
                    radius = cell*(.43 if p else .095)
                    cx,cy=x+cell/2,y+cell/2
                    c.create_oval(cx-radius,cy-radius,cx+radius,cy+radius,outline="#315b4b",width=3,fill="" if p else "#315b4b")
                if row==7: c.create_text(x+cell/2,y+cell+10,text=chess.FILE_NAMES[chess.square_file(sq)],fill=MUTED)
                if col==0: c.create_text(x-10,y+cell/2,text=chess.square_rank(sq)+1,fill=MUTED)

    def click(self,e):
        if not self.state or self.state["result"] or self.state["event"] or not self.mine(): return
        x,y,cell = self.geometry
        col,row=(e.x-x)//cell,(e.y-y)//cell
        if not (0<=col<8 and 0<=row<8): return
        sq = self.square(col,row)
        moves = [m for m in self.board.legal_moves if m.from_square==self.selected and m.to_square==sq]
        if moves:
            move=moves[0]
            if move.promotion:
                choice=simpledialog.askstring("Превращение","Ферзь (q), ладья (r), слон (b) или конь (n):",initialvalue="q")
                move=next((m for m in moves if chess.piece_symbol(m.promotion)==(choice or "").strip().lower()),None)
                if not move or self.state["event"]: return
            if self.role=="guest": self.link.outbox.put(dict(type="move",uci=move.uci(),fen=self.state["fen"]))
            elif self.game.move(move.uci()): self.publish()
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
            if self.role=="host":
                if typ=="ready" and not self.game:
                    self.begin(bool(self.external_path and data.get("external") is True))
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
            messagebox.showinfo("Сетевой стол",data)

    def poll(self):
        try:
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
                    messagebox.showerror("Undertale Boss Fight","Процесс завершился с кодом %d. Проверьте сборку и ресурсы. Энергия сохранена." % code)
                if self.training:
                    self.practice_done(code==10)
                    return
                self.finish(code==10 if self.state["event"]["kind"]=="mate" else code not in (0,11))
            g=self.game
            if g and not g.result:
                if not g.event and now>=self.deadline:
                    g.challenge("external" if g.external else "arena")
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
            messagebox.showerror("Ошибка партии",str(exc))
        finally:
            self.root.after(50,self.poll)

    def leave(self):
        if self.state["result"] or messagebox.askyesno("Завершить партию?","Вернуться к настройкам и закрыть текущую партию?"):
            self.reset()

    def reset(self):
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
        self.worker.shutdown(wait=False,cancel_futures=True)
        if self.link: self.link.close()
        self.stop_encounter()
        self.root.destroy()


if __name__=="__main__":
    App(tk.Tk()).root.mainloop()
