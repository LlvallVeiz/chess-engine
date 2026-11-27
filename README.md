# chess-engine

A chess engine built from scratch in Python — standard library only, no
external dependencies. Board representation, full legal move generation,
check/checkmate/stalemate and draw detection, minimax search with
alpha-beta pruning, and a terminal CLI to play against the engine.

## Features

- **Board representation** — flat 64-square array (`a1 == 0`, `h8 == 63`).
- **Legal move generation for all pieces**, including:
  - pawns: single/double push, captures, en passant, promotion to Q/R/B/N;
  - knights, bishops, rooks, queens, king;
  - castling kingside and queenside for both colours, with all legality
    conditions (king and rook unmoved, squares between empty, king not in
    check, not passing through check, not landing in check).
  - Legality is enforced by making each pseudo-legal move and verifying
    the moving side's king is not left in check — this automatically
    handles pins, including the subtle en-passant pin case.
- **Game-end detection** — check, checkmate, stalemate, insufficient
  material (K vs K, K+B vs K, K+N vs K), fifty-move rule, threefold
  repetition.
- **Search** — negamax with alpha-beta pruning and MVV-LVA capture
  ordering.
- **Evaluation** — material (P=100, N=320, B=330, R=500, Q=900, K=0) plus
  piece-square tables. The tables are the classic ones from Tomasz
  Michniewski's "Programming a chess engine" tutorial
  (https://www.chessprogramming.org/Simplified_Evaluation_Function),
  stored from White's point of view and mirrored for Black.
- **Perft** — move-count verification at any depth.
- **FEN** — full parsing and generation (placement, side to move,
  castling rights, en-passant square, halfmove clock, fullmove number).

## Requirements

Python 3.8+ (developed and tested on Python 3.12). No dependencies.

## Usage

Run from the project root:

```bash
# Play against the engine in the terminal (ASCII board)
python -m chess_engine play --depth 2            # you play White
python -m chess_engine play --depth 3 --colour black

# Count legal moves from the start position
python -m chess_engine perft --depth 3
python -m chess_engine perft --fen "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1" --depth 2

# Find the best move in a position
python -m chess_engine analyze --fen "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1" --depth 3
```

In `play`, enter moves in coordinate notation (`e2e4`, promotion `e7e8q`),
`O-O` / `O-O-O` to castle, `moves` to list legal moves, `quit` to stop.
Difficulty is the search depth (`--depth`, default 2; depth 3 is a
reasonable challenge, depth 4+ gets slow in pure Python).

## Perft verification

Counts match the standard reference positions from the Chess Programming
Wiki perft suite (verified by the test suite, `tests/test_perft.py`):

| Position | Depth 1 | Depth 2 | Depth 3 | Depth 4 |
|---|---:|---:|---:|---:|
| Start position | 20 | 400 | 8,902 | 197,281 |
| Kiwipete (`r3k2r/p1ppqpb1/...`) | 48 | 2,039 | 97,862 | — |

## Tests

```bash
python -m unittest discover -s tests -v
```

35 tests, all passing (~3.5 s), covering:

- perft counts above (start position depth 1–4, Kiwipete depth 1–3);
- checkmate (Fool's mate) and stalemate on known FENs;
- en passant: a legal capture, and the classic pin case where the
  en-passant capture is illegal because it would expose the king;
- castling: both sides for both colours, illegal through check, illegal
  while in check, rights lost after a rook move;
- promotion: a pawn on the 7th rank generates exactly 4 promotion moves;
- draws: insufficient material, fifty-move rule, threefold repetition;
- FEN round-trip (parse → generate returns the identical string);
- search: the engine takes a hanging queen (depth 2) and finds mate in 1.

## Project layout

```
chess_engine/
  __init__.py     public API (Board, Move, evaluate, search_best_move)
  __main__.py     `python -m chess_engine` entry point
  board.py        representation, move generation, rules, FEN, perft
  search.py       evaluation (material + PSTs), negamax + alpha-beta
  cli.py          play / perft / analyze commands, ASCII board
tests/
  test_perft.py   perft reference counts
  test_rules.py   mate/stalemate, en passant, castling, promotion, draws
  test_fen.py     FEN round-trips
  test_search.py  evaluation and engine decisions
```

## Known limits

- Pure-Python move generation: perft depth 4 from the start takes ~2 s;
  search beyond depth 3–4 in the middlegame is slow (no transposition
  table, no quiescence search, no iterative deepening).
- Evaluation is middlegame-only (a single king table; no endgame king
  table, no pawn-structure or mobility terms), so play strength is
  casual-club level at best — roughly, it plays sound tactics but has no
  positional understanding.
- No UCI/XBoard protocol support — the CLI is the only interface.
- Threefold repetition is tracked only within the current game session
  (positions from `set_fen` start a fresh history).
