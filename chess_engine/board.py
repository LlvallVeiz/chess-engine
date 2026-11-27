"""Board representation, move generation, and game rules.

Board layout: a flat list of 64 squares, index ``0 == a1`` and ``63 == h8``
(``square = rank * 8 + file`` with rank 0 = rank 1). Pieces are single
characters: ``'P','N','B','R','Q','K'`` for White (uppercase) and
``'p','n','b','r','q','k'`` for Black (lowercase); empty squares are ``None``.

Everything is pure Python standard library. Move generation is
pseudo-legal first, then filtered by making the move and checking that the
moving side's king is not left in check -- this automatically handles pins,
including the tricky en-passant pin case.
"""

from __future__ import annotations

WHITE = "w"
BLACK = "b"

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

FILES = "abcdefgh"

KNIGHT_OFFSETS = ((1, 2), (2, 1), (2, -1), (1, -2),
                  (-1, -2), (-2, -1), (-2, 1), (-1, 2))
KING_OFFSETS = ((1, 0), (1, 1), (0, 1), (-1, 1),
                (-1, 0), (-1, -1), (0, -1), (1, -1))
BISHOP_DIRS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
ROOK_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def sq_name(sq: int) -> str:
    """Square index -> algebraic name, e.g. 0 -> 'a1', 63 -> 'h8'."""
    return FILES[sq % 8] + str(sq // 8 + 1)


def sq_index(name: str) -> int:
    """Algebraic name -> square index, e.g. 'e4' -> 28."""
    return (int(name[1]) - 1) * 8 + FILES.index(name[0])


def _on_board(rank: int, file_: int) -> bool:
    return 0 <= rank < 8 and 0 <= file_ < 8


class Move:
    """A chess move.

    ``promotion`` is one of ``'Q'``, ``'R'``, ``'B'``, ``'N'`` (always given
    in uppercase; the colour is taken from the moving side) or ``None``.
    ``is_ep`` marks an en-passant capture and ``is_castle`` a castling move.
    """

    __slots__ = ("from_sq", "to_sq", "promotion", "is_ep", "is_castle")

    def __init__(self, from_sq, to_sq, promotion=None, is_ep=False,
                 is_castle=False):
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.promotion = promotion
        self.is_ep = is_ep
        self.is_castle = is_castle

    def __eq__(self, other):
        return (isinstance(other, Move)
                and (self.from_sq, self.to_sq, self.promotion,
                     self.is_ep, self.is_castle)
                == (other.from_sq, other.to_sq, other.promotion,
                    other.is_ep, other.is_castle))

    def __hash__(self):
        return hash((self.from_sq, self.to_sq, self.promotion,
                     self.is_ep, self.is_castle))

    def __repr__(self):
        return "Move(%s%s%s)" % (sq_name(self.from_sq), sq_name(self.to_sq),
                                 (self.promotion or "").lower())

    def uci(self) -> str:
        s = sq_name(self.from_sq) + sq_name(self.to_sq)
        if self.promotion:
            s += self.promotion.lower()
        return s


class Board:
    """A chess position with full FEN state and legal move generation."""

    def __init__(self, fen: str = START_FEN):
        self.pieces: list = [None] * 64
        self.turn = WHITE
        self.castling = ""      # subset of "KQkq", in FEN order
        self.ep_square = None   # square index, or None
        self.halfmove = 0
        self.fullmove = 1
        self._history_keys: list = []
        self.set_fen(fen)

    # ------------------------------------------------------------------ FEN
    def set_fen(self, fen: str) -> None:
        parts = fen.split()
        if len(parts) != 6:
            raise ValueError("FEN must have 6 fields: %r" % fen)
        placement, turn, castling, ep, halfmove, fullmove = parts
        pieces = [None] * 64
        rank, file_ = 7, 0
        for ch in placement:
            if ch == "/":
                rank -= 1
                file_ = 0
            elif ch.isdigit():
                file_ += int(ch)
            else:
                if ch not in "PNBRQKpnbrqk":
                    raise ValueError("bad piece in FEN: %r" % ch)
                pieces[rank * 8 + file_] = ch
                file_ += 1
        if turn not in (WHITE, BLACK):
            raise ValueError("bad side to move in FEN: %r" % turn)
        if castling != "-":
            for c in castling:
                if c not in "KQkq":
                    raise ValueError("bad castling field in FEN: %r" % castling)
        self.pieces = pieces
        self.turn = turn
        self.castling = "" if castling == "-" else castling
        self.ep_square = None if ep == "-" else sq_index(ep)
        self.halfmove = int(halfmove)
        self.fullmove = int(fullmove)
        self._history_keys = [self._position_key()]

    def fen(self) -> str:
        rows = []
        for rank in range(7, -1, -1):
            empty = 0
            row = ""
            for file_ in range(8):
                p = self.pieces[rank * 8 + file_]
                if p is None:
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += p
            if empty:
                row += str(empty)
            rows.append(row)
        ep = "-" if self.ep_square is None else sq_name(self.ep_square)
        return "%s %s %s %s %d %d" % (
            "/".join(rows), self.turn,
            self.castling if self.castling else "-",
            ep, self.halfmove, self.fullmove)

    def _position_key(self):
        """Position identity for repetition: pieces, turn, castling, ep."""
        return (tuple(self.pieces), self.turn, self.castling, self.ep_square)

    # ------------------------------------------------------------- helpers
    def king_square(self, color: str) -> int:
        target = "K" if color == WHITE else "k"
        return self.pieces.index(target)

    def _piece_color(self, piece) -> str | None:
        if piece is None:
            return None
        return WHITE if piece.isupper() else BLACK

    def is_square_attacked(self, sq: int, by: str) -> bool:
        """True if square ``sq`` is attacked by any piece of colour ``by``."""
        rank, file_ = sq // 8, sq % 8
        # Pawns: a white pawn on (rank-1) attacks (rank); a black pawn on
        # (rank+1) attacks (rank).
        pawn = "P" if by == WHITE else "p"
        pr = rank - 1 if by == WHITE else rank + 1
        for df in (-1, 1):
            if _on_board(pr, file_ + df):
                if self.pieces[pr * 8 + file_ + df] == pawn:
                    return True
        knight = "N" if by == WHITE else "n"
        king = "K" if by == WHITE else "k"
        for dr, df in KNIGHT_OFFSETS:
            r, f = rank + dr, file_ + df
            if _on_board(r, f) and self.pieces[r * 8 + f] == knight:
                return True
        for dr, df in KING_OFFSETS:
            r, f = rank + dr, file_ + df
            if _on_board(r, f) and self.pieces[r * 8 + f] == king:
                return True
        bishop = "B" if by == WHITE else "b"
        queen = "Q" if by == WHITE else "q"
        for dr, df in BISHOP_DIRS:
            r, f = rank + dr, file_ + df
            while _on_board(r, f):
                p = self.pieces[r * 8 + f]
                if p is not None:
                    if p == bishop or p == queen:
                        return True
                    break
                r += dr
                f += df
        rook = "R" if by == WHITE else "r"
        for dr, df in ROOK_DIRS:
            r, f = rank + dr, file_ + df
            while _on_board(r, f):
                p = self.pieces[r * 8 + f]
                if p is not None:
                    if p == rook or p == queen:
                        return True
                    break
                r += dr
                f += df
        return False

    def in_check(self, color: str) -> bool:
        return self.is_square_attacked(
            self.king_square(color), BLACK if color == WHITE else WHITE)

    # ------------------------------------------------------- move generation
    def _pawn_moves(self, sq: int, moves: list) -> None:
        rank, file_ = sq // 8, sq % 8
        white = self.turn == WHITE
        direction = 1 if white else -1
        start_rank = 1 if white else 6
        last_rank = 7 if white else 0
        own = self.pieces[sq]
        enemy = BLACK if white else WHITE

        def add_push(to_rank, to_file):
            to = to_rank * 8 + to_file
            if to_rank == last_rank:
                for promo in ("Q", "R", "B", "N"):
                    moves.append(Move(sq, to, promotion=promo))
            else:
                moves.append(Move(sq, to))

        # Single and double push.
        one = rank + direction
        if _on_board(one, file_) and self.pieces[one * 8 + file_] is None:
            add_push(one, file_)
            two = rank + 2 * direction
            if rank == start_rank and self.pieces[two * 8 + file_] is None:
                moves.append(Move(sq, two * 8 + file_))
        # Captures (including en passant).
        for df in (-1, 1):
            f = file_ + df
            if not _on_board(one, f):
                continue
            to = one * 8 + f
            target = self.pieces[to]
            if target is not None and self._piece_color(target) == enemy:
                if one == last_rank:
                    for promo in ("Q", "R", "B", "N"):
                        moves.append(Move(sq, to, promotion=promo))
                else:
                    moves.append(Move(sq, to))
            elif to == self.ep_square:
                moves.append(Move(sq, to, is_ep=True))

    def _slider_moves(self, sq: int, dirs, moves: list) -> None:
        rank, file_ = sq // 8, sq % 8
        enemy = BLACK if self.turn == WHITE else WHITE
        for dr, df in dirs:
            r, f = rank + dr, file_ + df
            while _on_board(r, f):
                to = r * 8 + f
                target = self.pieces[to]
                if target is None:
                    moves.append(Move(sq, to))
                else:
                    if self._piece_color(target) == enemy:
                        moves.append(Move(sq, to))
                    break
                r += dr
                f += df

    def _leaper_moves(self, sq: int, offsets, moves: list) -> None:
        rank, file_ = sq // 8, sq % 8
        me = self.turn
        for dr, df in offsets:
            r, f = rank + dr, file_ + df
            if not _on_board(r, f):
                continue
            to = r * 8 + f
            target = self.pieces[to]
            if target is None or self._piece_color(target) != me:
                moves.append(Move(sq, to))

    def _castling_moves(self, moves: list) -> None:
        """Append legal castling moves for the side to move.

        Castling is legal only if: the right still exists, the squares
        between king and rook are empty, and the king is not in check, does
        not pass through check, and does not land in check.
        """
        white = self.turn == WHITE
        enemy = BLACK if white else WHITE
        king_sq = 4 if white else 60
        if self.pieces[king_sq] != ("K" if white else "k"):
            return
        rights = ("K", "Q") if white else ("k", "q")
        # Kingside: squares f/g empty, king e/f/g not attacked.
        if rights[0] in self.castling:
            between = (5, 6) if white else (61, 62)
            rook_sq = 7 if white else 63
            if (self.pieces[rook_sq] == ("R" if white else "r")
                    and all(self.pieces[s] is None for s in between)
                    and not self.is_square_attacked(king_sq, enemy)
                    and not self.is_square_attacked(between[0], enemy)
                    and not self.is_square_attacked(between[1], enemy)):
                moves.append(Move(king_sq, between[1], is_castle=True))
        # Queenside: squares b/c/d empty, king e/d/c not attacked.
        if rights[1] in self.castling:
            between = (1, 2, 3) if white else (57, 58, 59)
            rook_sq = 0 if white else 56
            if (self.pieces[rook_sq] == ("R" if white else "r")
                    and all(self.pieces[s] is None for s in between)
                    and not self.is_square_attacked(king_sq, enemy)
                    and not self.is_square_attacked(3 if white else 59, enemy)
                    and not self.is_square_attacked(2 if white else 58, enemy)):
                moves.append(Move(king_sq, between[1], is_castle=True))

    def pseudo_legal_moves(self) -> list:
        moves = []
        for sq, piece in enumerate(self.pieces):
            if piece is None or self._piece_color(piece) != self.turn:
                continue
            kind = piece.upper()
            if kind == "P":
                self._pawn_moves(sq, moves)
            elif kind == "N":
                self._leaper_moves(sq, KNIGHT_OFFSETS, moves)
            elif kind == "B":
                self._slider_moves(sq, BISHOP_DIRS, moves)
            elif kind == "R":
                self._slider_moves(sq, ROOK_DIRS, moves)
            elif kind == "Q":
                self._slider_moves(sq, BISHOP_DIRS + ROOK_DIRS, moves)
            elif kind == "K":
                self._leaper_moves(sq, KING_OFFSETS, moves)
        self._castling_moves(moves)
        return moves

    def legal_moves(self) -> list:
        """All fully legal moves for the side to move."""
        legal = []
        mover = self.turn
        for move in self.pseudo_legal_moves():
            undo = self.make_move(move)
            if not self.in_check(mover):
                legal.append(move)
            self.unmake_move(move, undo)
        return legal

    # ------------------------------------------------------------ make/unmake
    def make_move(self, move: Move) -> dict:
        """Play ``move``; returns an undo record for :meth:`unmake_move`."""
        undo = {
            "pieces": self.pieces[:],
            "castling": self.castling,
            "ep_square": self.ep_square,
            "halfmove": self.halfmove,
            "fullmove": self.fullmove,
        }
        mover = self.turn
        piece = self.pieces[move.from_sq]
        captured_sq = move.to_sq
        if move.is_ep:
            # The captured pawn sits one rank behind the landing square.
            captured_sq = move.to_sq - 8 if mover == WHITE else move.to_sq + 8
        captured = self.pieces[captured_sq]

        self.pieces[move.from_sq] = None
        if move.promotion:
            self.pieces[move.to_sq] = (move.promotion if mover == WHITE
                                       else move.promotion.lower())
        else:
            self.pieces[move.to_sq] = piece
        if move.is_ep:
            self.pieces[captured_sq] = None
        if move.is_castle:
            # Move the rook to the other side of the king.
            if move.to_sq == 6:      # white kingside
                self.pieces[5], self.pieces[7] = self.pieces[7], None
            elif move.to_sq == 2:    # white queenside
                self.pieces[3], self.pieces[0] = self.pieces[0], None
            elif move.to_sq == 62:   # black kingside
                self.pieces[61], self.pieces[63] = self.pieces[63], None
            elif move.to_sq == 58:   # black queenside
                self.pieces[59], self.pieces[56] = self.pieces[56], None

        # Update castling rights: king move clears both rights for its
        # colour; a rook moving from (or being captured on) its home
        # square clears that side's right.
        rights = self.castling
        if piece.upper() == "K":
            rights = rights.replace("K", "").replace("Q", "") \
                if mover == WHITE else \
                rights.replace("k", "").replace("q", "")
        for sq, flag in ((0, "Q"), (7, "K"), (56, "q"), (63, "k")):
            if move.from_sq == sq or move.to_sq == sq:
                rights = rights.replace(flag, "")
        self.castling = rights

        # En passant square: set only after a double pawn push.
        if piece.upper() == "P" and abs(move.to_sq - move.from_sq) == 16:
            self.ep_square = (move.from_sq + move.to_sq) // 2
        else:
            self.ep_square = None

        # Halfmove clock resets on pawn moves and captures.
        if piece.upper() == "P" or captured is not None:
            self.halfmove = 0
        else:
            self.halfmove += 1
        if mover == BLACK:
            self.fullmove += 1
        self.turn = BLACK if mover == WHITE else WHITE
        self._history_keys.append(self._position_key())
        return undo

    def unmake_move(self, move: Move, undo: dict) -> None:
        self.pieces = undo["pieces"]
        self.castling = undo["castling"]
        self.ep_square = undo["ep_square"]
        self.halfmove = undo["halfmove"]
        self.fullmove = undo["fullmove"]
        self.turn = BLACK if self.turn == WHITE else WHITE
        self._history_keys.pop()

    # ------------------------------------------------------------- game state
    def is_checkmate(self) -> bool:
        return self.in_check(self.turn) and not self.legal_moves()

    def is_stalemate(self) -> bool:
        return not self.in_check(self.turn) and not self.legal_moves()

    def insufficient_material(self) -> bool:
        """K vs K, K+B vs K, K+N vs K (also K+B vs K+B same colour bishops
        is a draw in FIDE terms only when bishops are on the same colour;
        the simple cases below are the ones that can never mate)."""
        minors = [p for p in self.pieces if p is not None
                  and p.upper() not in ("K",)]
        if not minors:
            return True  # bare kings
        if len(minors) == 1 and minors[0].upper() in ("B", "N"):
            return True
        return False

    def is_threefold_repetition(self) -> bool:
        key = self._position_key()
        return self._history_keys.count(key) >= 3

    def is_fifty_move_draw(self) -> bool:
        return self.halfmove >= 100

    def is_draw(self) -> bool:
        return (self.is_stalemate()
                or self.insufficient_material()
                or self.is_fifty_move_draw()
                or self.is_threefold_repetition())

    def game_status(self) -> str:
        """'checkmate', 'stalemate', 'draw', 'check', or 'ongoing'."""
        if self.is_checkmate():
            return "checkmate"
        if self.is_stalemate():
            return "stalemate"
        if self.insufficient_material() or self.is_fifty_move_draw() \
                or self.is_threefold_repetition():
            return "draw"
        return "check" if self.in_check(self.turn) else "ongoing"

    def perft(self, depth: int) -> int:
        """Count leaf nodes at ``depth`` (legal-move count at depth 1)."""
        if depth == 0:
            return 1
        nodes = 0
        for move in self.legal_moves():
            undo = self.make_move(move)
            nodes += self.perft(depth - 1)
            self.unmake_move(move, undo)
        return nodes

    # --------------------------------------------------------------- display
    def ascii_board(self) -> str:
        lines = []
        for rank in range(7, -1, -1):
            row = []
            for file_ in range(8):
                p = self.pieces[rank * 8 + file_]
                row.append(p if p is not None else ".")
            lines.append("%d  %s" % (rank + 1, " ".join(row)))
        lines.append("   " + " ".join(FILES))
        return "\n".join(lines)
