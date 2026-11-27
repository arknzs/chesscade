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
        if self.result or not self.event or self.event["id"] != event_id:
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
        return dict(charges=self.charges[:], delay=[max(0,t-time.monotonic()) for t in self.ready], fen=self.board.fen(), hp=self.hp[:], event=self.event, result=self.result,
                    history=self.history[-12:], last=self.board.peek().uci() if self.board.move_stack else "",
                    interval=self.interval, qte=self.qte, external=self.external,
                    claim=not self.result and not self.event and self.board.can_claim_draw())
