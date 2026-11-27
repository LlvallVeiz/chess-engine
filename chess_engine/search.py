"""Search (negamax with alpha-beta pruning) and evaluation.

Evaluation = material + piece-square tables. Material values (centipawns):
pawn 100, knight 320, bishop 330, rook 500, queen 900, king 0.

Piece-square tables are the classic ones published by Tomasz Michniewski
in his "Programming a chess engine" tutorial
(https://www.chessprogramming.org/Simplified_Evaluation_Function),
written here from White's point of view (rank 8 first) and mirrored for
Black. They are simple, well-known, and good enough for a casual engine.
"""

from __future__ import annotations

from .board import Board, Move, WHITE, BLACK

MATERIAL = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0}

# Tables are listed rank 8 -> rank 1 (a8..h8 first row), as in Michniewski's
# article. Indexing below converts to our a1 == 0 board layout.
PAWN_TABLE = [
    0, 0, 0, 0, 0, 0, 0, 0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5, 5, 10, 25, 25, 10, 5, 5,
    0, 0, 0, 20, 20, 0, 0, 0,
    5, -5, -10, 0, 0, -10, -5, 5,
    5, 10, 10, -20, -20, 10, 10, 5,
    0, 0, 0, 0, 0, 0, 0, 0,
]
KNIGHT_TABLE = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20, 0, 0, 0, 0, -20, -40,
    -30, 0, 10, 15, 15, 10, 0, -30,
    -30, 5, 15, 20, 20, 15, 5, -30,
    -30, 0, 15, 20, 20, 15, 0, -30,
    -30, 5, 10, 15, 15, 10, 5, -30,
    -40, -20, 0, 5, 5, 0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]
BISHOP_TABLE = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 10, 10, 5, 0, -10,
    -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 10, 10, 10, 10, 10, 10, -10,
    -10, 5, 0, 0, 0, 0, 5, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]
ROOK_TABLE = [
    0, 0, 0, 0, 0, 0, 0, 0,
    5, 10, 10, 10, 10, 10, 10, 5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    0, 0, 0, 5, 5, 0, 0, 0,
]
QUEEN_TABLE = [
    -20, -10, -10, -5, -5, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 5, 5, 5, 0, -10,
    -5, 0, 5, 5, 5, 5, 0, -5,
    0, 0, 5, 5, 5, 5, 0, -5,
    -10, 5, 5, 5, 5, 5, 0, -10,
    -10, 0, 5, 0, 0, 0, 0, -10,
    -20, -10, -10, -5, -5, -10, -10, -20,
]
KING_MIDDLEGAME_TABLE = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    20, 20, 0, 0, 0, 0, 20, 20,
    20, 30, 10, 0, 0, 10, 30, 20,
]

PST = {
    "P": PAWN_TABLE, "N": KNIGHT_TABLE, "B": BISHOP_TABLE,
    "R": ROOK_TABLE, "Q": QUEEN_TABLE, "K": KING_MIDDLEGAME_TABLE,
}

# Mate scores: any score above this means a forced mate is on the board.
MATE_SCORE = 100000


def _pst_index(sq: int, white_piece: bool) -> int:
    """Convert our a1==0 square to the table's a8-first indexing.

    Tables are stored rank 8 first, so a White piece on square ``sq``
    (rank = sq // 8, file = sq % 8) reads table index
    ``(7 - rank) * 8 + file``. A Black piece reads the vertically mirrored
    entry, i.e. ``rank * 8 + file``.
    """
    rank, file_ = sq // 8, sq % 8
    if white_piece:
        return (7 - rank) * 8 + file_
    return rank * 8 + file_


def evaluate(board: Board) -> int:
    """Static evaluation in centipawns, from White's point of view.

    Positive means good for White, negative means good for Black.
    """
    score = 0
    for sq, piece in enumerate(board.pieces):
        if piece is None:
            continue
        kind = piece.upper()
        value = MATERIAL[kind] + PST[kind][_pst_index(sq, piece.isupper())]
        score += value if piece.isupper() else -value
    return score


def _order_moves(board: Board, moves: list) -> list:
    """Order moves so alpha-beta prunes well: captures first, scored by
    most-valuable-victim / least-valuable-attacker, then the rest."""
    def score(move: Move) -> int:
        target = board.pieces[move.to_sq]
        if move.is_ep:
            target = "p" if board.turn == WHITE else "P"
        if target is None:
            return 0
        attacker = board.pieces[move.from_sq]
        victim = MATERIAL[target.upper()]
        return 10 * victim - MATERIAL[attacker.upper()]
    return sorted(moves, key=score, reverse=True)


def _negamax(board: Board, depth: int, alpha: int, beta: int,
             ply: int) -> int:
    """Negamax search; returns the score from the side-to-move's view."""
    if depth == 0:
        # Evaluate from the side to move's perspective.
        ev = evaluate(board)
        return ev if board.turn == WHITE else -ev
    moves = _order_moves(board, board.legal_moves())
    if not moves:
        if board.in_check(board.turn):
            # Checkmated: prefer faster mates (subtract ply).
            return -MATE_SCORE + ply
        return 0  # stalemate
    best = -MATE_SCORE - 1
    for move in moves:
        undo = board.make_move(move)
        score = -_negamax(board, depth - 1, -beta, -alpha, ply + 1)
        board.unmake_move(move, undo)
        if score > best:
            best = score
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    return best


def search_best_move(board: Board, depth: int):
    """Return ``(best_move, score)`` at the given depth.

    ``score`` is in centipawns from the side-to-move's point of view.
    ``best_move`` is ``None`` when there are no legal moves.
    """
    moves = _order_moves(board, board.legal_moves())
    if not moves:
        return None, 0
    best_move, best_score = None, -MATE_SCORE - 1
    alpha, beta = -MATE_SCORE - 1, MATE_SCORE + 1
    for move in moves:
        undo = board.make_move(move)
        score = -_negamax(board, depth - 1, -beta, -alpha, 1)
        board.unmake_move(move, undo)
        if score > best_score:
            best_score, best_move = score, move
        if score > alpha:
            alpha = score
    return best_move, best_score


def score_to_text(score: int) -> str:
    """Human-readable score, e.g. '+1.25' or '#3' (mate in 3)."""
    if abs(score) >= MATE_SCORE - 1000:
        mate_in = (MATE_SCORE - abs(score) + 1) // 2
        return "#%d" % mate_in if score > 0 else "-#%d" % mate_in
    sign = "+" if score >= 0 else "-"
    return "%s%.2f" % (sign, abs(score) / 100.0)
