"""Search / evaluation tests: the engine finds hanging pieces."""

import unittest

from chess_engine.board import Board
from chess_engine.search import evaluate, search_best_move, score_to_text


class TestEvaluation(unittest.TestCase):
    def test_start_position_is_balanced(self):
        self.assertEqual(evaluate(Board()), 0)

    def test_material_advantage(self):
        # White is a queen up.
        board = Board("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")
        self.assertGreater(evaluate(board), 800)

    def test_evaluation_is_antisymmetric(self):
        white_up = Board("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")
        black_up = Board("4K3/8/8/8/8/8/8/3qk3 w - - 0 1")
        self.assertEqual(evaluate(white_up), -evaluate(black_up))


class TestSearch(unittest.TestCase):
    def test_engine_takes_hanging_queen(self):
        # Black queen on d3 is undefended; white pawn e2 can take it.
        # Start eval is about -825 (black is a queen up); after exd3
        # White is just a pawn up, so the search score is ~+90, not ~+900
        # -- the swing, not the absolute value, is the queen.
        board = Board("4k3/8/8/8/8/3q4/4P3/4K3 w - - 0 1")
        self.assertLess(evaluate(board), -500)
        move, score = search_best_move(board, 2)
        self.assertIsNotNone(move)
        self.assertEqual(move.uci(), "e2d3")
        self.assertGreater(score, 0)
        self.assertGreater(score, evaluate(board))

    def test_engine_finds_mate_in_one(self):
        # Back-rank mate: white rook to e8 is mate.
        board = Board("6k1/5ppp/8/8/8/8/8/4R1K1 w - - 0 1")
        move, score = search_best_move(board, 2)
        self.assertIsNotNone(move)
        self.assertEqual(move.uci(), "e1e8")
        self.assertIn("#", score_to_text(score))

    def test_no_move_when_checkmated(self):
        board = Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR "
                      "w KQkq - 1 2")
        move, _ = search_best_move(board, 2)
        self.assertIsNone(move)

    def test_score_text(self):
        self.assertEqual(score_to_text(125), "+1.25")
        self.assertEqual(score_to_text(-50), "-0.50")
        self.assertEqual(score_to_text(0), "+0.00")


if __name__ == "__main__":
    unittest.main()
