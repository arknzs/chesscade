import random
import time
import chess


MAX_ENERGY = 5


class Match:
    def __init__(self, interval, qte, external):
        self.board = chess.Board()
        self.interval = interval
        self.qte = qte
        self.external = external
        self.charges=[3,3]
        self.ready=[0.,0.]
        self.hp = [MAX_ENERGY, MAX_ENERGY]
        self.event = None
        self.serial = 0
        self.history = []
        self.result = ""
        self.notice = ""

    def challenge(self, kind, move=""):
        self.serial += 1
        self.event = dict(kind=kind, move=move, id=self.serial, seed=random.randrange(1000000))

    def throw(self, sender):
        now=time.monotonic()
        if self.result or self.event or sender==self.board.turn or not self.charges[sender] or now<self.ready[sender]:
            return False
        self.charges[sender]-=1
        self.ready[sender]=now+60
        self.challenge("duel")
        return True

    def action(self, sender, kind):
        if self.result or self.event or kind not in ("undo","draw","resign","energy"):
            return False
        if kind=="resign":
            self.result="Сдались " + ("белые · победа чёрных" if sender else "чёрные · победа белых")
            return True
        count=2 if self.board.turn==sender else 1
        if kind=="undo" and len(self.history)<count:
            return False
        self.challenge("offer")
        self.event.update(action=kind,sender=sender,count=count)
        return True

    def reply(self, sender, ident, accepted):
        offer=self.event
        if not offer or offer["kind"]!="offer" or offer["id"]!=ident or offer["sender"]==sender:
            return False
        self.event=None
        if accepted and offer["action"]=="draw":
            self.result="Ничья по соглашению"
        elif accepted and offer["action"]=="energy":
            self.challenge("survival")
        elif accepted:
            for _ in range(offer["count"]):
                self.board.pop()
                self.history.pop()
        return True

    def end_survival(self,dead):
        if not self.event or self.event["kind"] not in ("survival","duel","arena"): return
        event,self.event=self.event,None
        if event["kind"]!="survival":
            for side in dead:
                self.hp[side]=max(0,self.hp[side]-1)
            if self.hp==[0,0]: self.result="Ничья по сердцам"
            elif 0 in self.hp: self.result="Победа "+("белых" if self.hp[1] else "чёрных")+" по сердцам"
            elif event["move"] and self.board.turn not in dead:
                self.commit(chess.Move.from_uci(event["move"]))
            return
        if not dead: return
        if len(dead)==2:
            self.notice="Одновременное поражение · ничья"
        else:
            winner=1-dead[0]
            self.hp[winner]=MAX_ENERGY
            self.notice=("Белые" if winner else "Чёрные")+" восполнили энергию до 5"

    def end_circuit(self,scores):
        if not self.event or self.event["kind"]!="maze": return
        self.event=None
        self.notice="Контур · %d : %d"%(scores[1],scores[0])
        if scores[0]!=scores[1]:
            winner=int(scores[1]>scores[0])
            self.hp[winner]=min(MAX_ENERGY,self.hp[winner]+2)
            self.notice+=" · победа "+("белых" if winner else "чёрных")

    def move(self, uci):
        if self.result or self.event:
            return False
        try:
            move = self.board.parse_uci(uci)
        except (ValueError, TypeError, AttributeError):
            return False
        if not move:
            return False
        if self.qte and self.board.is_capture(move):
            self.challenge("qte", uci)
        else:
            self.commit(move)
        return True

    def commit(self, move):
        prefix = str(self.board.fullmove_number) + "." if self.board.turn else ""
        self.history.append(prefix + self.board.san(move))
        self.board.push(move)
        outcome = self.board.outcome()
        if outcome:
            if outcome.winner is None:
                self.result = "Ничья"
            else:
                self.challenge("mate")

    def finish(self, event_id, success):
        if self.result or not self.event or self.event["kind"] in ("offer","survival","duel","arena","maze") or self.event["id"] != event_id:
            return False
        event, self.event = self.event, None
        if event["kind"]=="mate":
            if success:
                for _ in range(min(5,len(self.board.move_stack))):
                    self.board.pop()
                    self.history.pop()
            else:
                self.result="Мат · победа " + ("чёрных" if self.board.turn else "белых")
        elif success and event["kind"] == "qte":
            self.commit(chess.Move.from_uci(event["move"]))
        elif not success:
            self.hp[int(self.board.turn)] -= 1
            if not self.hp[int(self.board.turn)]:
                self.result = "Победа " + ("чёрных" if self.board.turn else "белых") + " по энергии"
        return True

    def claim(self):
        if not self.event and not self.result and self.board.can_claim_draw():
            self.result = "Ничья по требованию"
            return True
        return False

    def state(self):
        return dict(notice=self.notice,charges=self.charges[:], delay=[max(0,t-time.monotonic()) for t in self.ready], fen=self.board.fen(), hp=self.hp[:], event=self.event, result=self.result,
                    history=self.history[-12:], last=self.board.peek().uci() if self.board.move_stack else "",
                    interval=self.interval, qte=self.qte, external=self.external,
                    claim=not self.result and not self.event and self.board.can_claim_draw())
