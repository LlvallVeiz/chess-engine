"""Command-line interface: play against the AI, perft, analyze."""

from __future__ import annotations

import argparse
import sys
import time

from .board import Board, Move, START_FEN, sq_index, sq_name
from .search import search_best_move, score_to_text, evaluate


def _parse_move(board: Board, text: str):
    """Parse a move typed by the user: 'e2e4', 'e7e8q', or 'O-O' / '0-0'."""
    text = text.strip()
    if text in ("O-O", "0-0", "o-o"):
        target = 6 if board.turn == "w" else 62
    elif text in ("O-O-O", "0-0-0", "o-o-o"):
        target = 2 if board.turn == "w" else 58
    else:
        if len(text) not in (4, 5):
            return None
        try:
            from_sq = sq_index(text[0:2])
            to_sq = sq_index(text[2:4])
        except (ValueError, IndexError):
            return None
        promo = text[4].upper() if len(text) == 5 else None
        if promo is not None and promo not in "QRBN":
            return None
        for move in board.legal_moves():
            if (move.from_sq == from_sq and move.to_sq == to_sq
                    and move.promotion == promo):
                return move
        return None
    for move in board.legal_moves():
        if move.is_castle and move.to_sq == target:
            return move
    return None


def _show(board: Board) -> None:
    print()
    print(board.ascii_board())
    print("FEN: %s" % board.fen())
    status = board.game_status()
    if status == "check":
        print("Check!")
    print("Side to move: %s" % ("White" if board.turn == "w" else "Black"))


def cmd_play(args) -> int:
    board = Board(args.fen) if args.fen else Board()
    depth = args.depth
    human = "w" if args.colour == "white" else "b"
    print("Chess engine — you play %s, engine depth %d." % (args.colour, depth))
    print("Enter moves like e2e4 (promotion: e7e8q), 'O-O' to castle,")
    print("'quit' to stop, 'moves' to list legal moves.")
    while True:
        _show(board)
        status = board.game_status()
        if status == "checkmate":
            winner = "Black" if board.turn == "w" else "White"
            print("Checkmate! %s wins." % winner)
            return 0
        if status == "stalemate":
            print("Stalemate — draw.")
            return 0
        if status == "draw":
            print("Draw.")
            return 0
        if board.turn == human:
            try:
                text = input("Your move: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGame aborted.")
                return 0
            if text.lower() in ("quit", "exit", "q"):
                print("Game aborted.")
                return 0
            if text.lower() == "moves":
                print(" ".join(m.uci() for m in board.legal_moves()))
                continue
            move = _parse_move(board, text)
            if move is None:
                print("Illegal move — try again (e.g. e2e4).")
                continue
            board.make_move(move)
        else:
            print("Engine thinking (depth %d)..." % depth)
            started = time.time()
            move, score = search_best_move(board, depth)
            print("Engine plays %s (eval %s, %.2fs)"
                  % (move.uci(), score_to_text(score), time.time() - started))
            board.make_move(move)
    return 0


def cmd_perft(args) -> int:
    board = Board(args.fen)
    if args.depth < 0:
        print("depth must be >= 0")
        return 2
    started = time.time()
    nodes = board.perft(args.depth)
    elapsed = time.time() - started
    print("perft(%d) = %d  (%.2fs, %d nps)"
          % (args.depth, nodes, elapsed,
             int(nodes / elapsed) if elapsed > 0 else 0))
    return 0


def cmd_analyze(args) -> int:
    board = Board(args.fen)
    print(board.ascii_board())
    print("FEN: %s" % board.fen())
    if not board.legal_moves():
        print("No legal moves: %s" % board.game_status())
        return 0
    started = time.time()
    move, score = search_best_move(board, args.depth)
    print("Best move: %s  (eval %s for side to move, depth %d, %.2fs)"
          % (move.uci(), score_to_text(score), args.depth,
             time.time() - started))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chess-engine",
        description="A chess engine built from scratch (stdlib only).")
    sub = parser.add_subparsers(dest="command", required=True)

    play = sub.add_parser("play", help="play against the engine in the terminal")
    play.add_argument("--depth", type=int, default=2,
                      help="engine search depth (default: 2)")
    play.add_argument("--colour", choices=["white", "black"], default="white",
                      help="which colour you play (default: white)")
    play.add_argument("--fen", default=None,
                      help="start from a FEN position instead of the start")
    play.set_defaults(func=cmd_play)

    perft = sub.add_parser("perft", help="count legal moves to a depth")
    perft.add_argument("--fen", default=START_FEN,
                       help="position in FEN (default: start position)")
    perft.add_argument("--depth", type=int, default=3,
                       help="depth (default: 3)")
    perft.set_defaults(func=cmd_perft)

    analyze = sub.add_parser("analyze", help="find the best move in a position")
    analyze.add_argument("--fen", default=START_FEN,
                         help="position in FEN (default: start position)")
    analyze.add_argument("--depth", type=int, default=3,
                         help="search depth (default: 3)")
    analyze.set_defaults(func=cmd_analyze)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
