"""chess-engine: a chess engine built from scratch (Python stdlib only)."""

from .board import Board, Move, START_FEN
from .search import evaluate, search_best_move, score_to_text

__all__ = ["Board", "Move", "START_FEN", "evaluate", "search_best_move",
           "score_to_text"]
__version__ = "0.1.0"
