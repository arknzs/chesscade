import chess
from PIL import Image, ImageDraw, ImageTk


class PieceSet:
    """Keep a set of rendered figures for the current board size."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.cell = 0
        self.icons = {}

    def draw(self, x, y, cell, piece):
        if cell != self.cell:
            self.cell = cell
            self.icons.clear()
        key = (piece.piece_type, piece.color)
        if key not in self.icons:
            self.icons[key] = ImageTk.PhotoImage(render_piece(cell, *key), master=self.canvas)
        self.canvas.create_image(x, y, image=self.icons[key], anchor="nw")


def render_piece(cell, kind, white):
    scale = 4
    image = Image.new("RGBA", (100*scale, 100*scale))
    ink = ImageDraw.Draw(image)
    body, panel, rim, accent = (
        ("#f4f0ff", "#d5c9ea", "#302344", "#277d88") if white else
        ("#281b40", "#493461", "#c3a5ec", "#72eee5")
    )

    def box(bounds):
        return tuple(coord*scale for coord in bounds)

    def points(coords):
        return [(x*scale, y*scale) for x,y in coords]

    def form(coords):
        ink.polygon(points(coords), fill=body, outline=rim, width=2*scale)

    def slab(bounds, radius, color, outline=None):
        ink.rounded_rectangle(box(bounds), radius*scale, fill=color, outline=outline, width=2*scale)

    def oval(bounds, color, outline=None):
        ink.ellipse(box(bounds), fill=color, outline=outline, width=2*scale)

    def line(coords, color, width=2):
        ink.line(points(coords), fill=color, width=width*scale, joint="curve")

    # The same stepped plinth ties the set together, with a smaller footprint for pawns.
    inset = 6 if kind == chess.PAWN else 0
    oval((18+inset, 84, 82-inset, 94), "#17132680")
    match kind:
        case chess.PAWN:
            form([(35,78),(36,70),(42,62),(45,48),(55,48),(58,62),(64,70),(65,78)])
            slab((39,47,61,53), 3, panel, rim)
            oval((39,25,61,47), body, rim)
            line([(43,33),(47,30),(52,30)], panel)
        case chess.KNIGHT:
            form([(24,78),(30,67),(39,59),(50,49),(46,42),(40,46),(32,55),(23,53),
                  (19,45),(27,34),(38,26),(43,15),(46,12),(55,23),(64,24),(73,34),
                  (78,47),(77,61),(70,78)])
            line([(61,29),(69,38),(73,48),(72,59),(66,71)], panel, 4)
            oval((40,31,46,37), accent)
            line([(24,47),(30,48),(35,44)], rim)
        case chess.BISHOP:
            form([(29,78),(35,70),(42,60),(43,52),(57,52),(58,60),(65,70),(71,78)])
            form([(50,13),(61,24),(68,36),(68,45),(64,52),(57,57),(43,57),
                  (36,52),(32,45),(32,36),(39,24)])
            line([(63,29),(52,40),(48,46)], accent, 4)
            slab((37,56,63,62), 3, panel, rim)
        case chess.ROOK:
            form([(24,78),(28,68),(34,59),(34,46),(25,39),(25,18),(36,18),(36,28),
                  (44,28),(44,18),(56,18),(56,28),(64,28),(64,18),(75,18),(75,39),
                  (66,46),(66,59),(72,68),(76,78)])
            line([(29,38),(71,38)], accent)
            line([(59,48),(59,61),(65,70)], panel, 3)
        case chess.QUEEN:
            form([(29,78),(35,68),(40,54),(21,27),(38,38),(37,21),(47,34),
                  (50,14),(53,34),(63,21),(62,38),(79,27),(60,54),(65,68),(71,78)])
            for x,y,r in [(21,27,4),(37,21,4),(50,14,5),(63,21,4),(79,27,4)]:
                oval((x-r,y-r,x+r,y+r), body, rim)
            line([(40,52),(50,55),(60,52)], accent, 3)
            form([(50,37),(54,43),(50,49),(46,43)])
        case chess.KING:
            form([(28,78),(35,69),(38,57),(26,43),(27,36),(32,31),(40,30),(50,36),
                  (60,30),(68,31),(73,36),(74,43),(62,57),(65,69),(72,78)])
            form([(46,34),(46,25),(36,25),(36,17),(46,17),(46,8),(54,8),(54,17),
                  (64,17),(64,25),(54,25),(54,34),(50,39)])
            line([(33,40),(43,44),(50,50),(57,44),(67,40)], panel, 3)
            line([(40,57),(60,57)], accent, 3)

    slab((25+inset,73,75-inset,83), 5, panel, rim)
    slab((20+inset,80,80-inset,90), 4, body, rim)
    line([(31+inset,85),(69-inset,85)], accent)
    return image.resize((cell,cell), Image.Resampling.LANCZOS)
