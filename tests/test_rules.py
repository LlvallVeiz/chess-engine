"""Rules tests: mate/stalemate, en passant, castling, promotion, draws."""

import unittest

from chess_engine.board import Board, Move, sq_index


def ucis(board):
    return {m.uci() for m in board.legal_moves()}


class TestMateAndStalemate(unittest.TestCase):
    def test_fools_mate_is_checkmate(self):
        # Fool's mate final position: black queen on h4 mates White.
        board = Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR "
                      "w KQkq - 1 2")
        self.assertTrue(board.in_check("w"))
        self.assertTrue(board.is_checkmate())
        self.assertEqual(board.game_status(), "checkmate")
        self.assertEqual(board.legal_moves(), [])

    def test_stalemate(self):
        board = Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        self.assertFalse(board.in_check("b"))
        self.assertTrue(board.is_stalemate())
        self.assertEqual(board.game_status(), "stalemate")

    def test_check_but_not_mate(self):
        # White queen gives check on e2; black king has escapes.
        board = Board("4k3/8/8/8/8/8/4Q3/4K3 b - - 0 1")
        self.assertTrue(board.in_check("b"))
        self.assertFalse(board.is_checkmate())
        self.assertEqual(board.game_status(), "check")


class TestEnPassant(unittest.TestCase):
    def test_en_passant_capture_is_legal(self):
        board = Board("rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR "
                      "w KQkq d6 0 2")
        self.assertIn("e5d6", ucis(board))
        board.make_move([m for m in board.legal_moves()
                         if m.uci() == "e5d6"][0])
        # The black pawn on d5 is gone after the capture.
        self.assertIsNone(board.pieces[sq_index("d5")])
        self.assertEqual(board.pieces[sq_index("d6")], "P")

    def test_en_passant_pin_is_illegal(self):
        # Rank 5: black rook a5, black pawn d5 (just double-pushed),
        # white pawn e5, white king h5. Playing exd6 e.p. would remove
        # both pawns from rank 5 and expose the king to the rook.
        board = Board("8/8/8/r2pP2K/8/8/8/8 w - d6 0 1")
        self.assertNotIn("e5d6", ucis(board))
        # The plain pawn push is still fine.
        self.assertIn("e5e6", ucis(board))

    def test_en_passant_square_only_after_double_push(self):
        board = Board()
        board.make_move([m for m in board.legal_moves()
                         if m.uci() == "e2e4"][0])
        self.assertEqual(board.ep_square, sq_index("e3"))
        board.make_move([m for m in board.legal_moves()
                         if m.uci() == "a7a6"][0])
        self.assertIsNone(board.ep_square)


class TestCastling(unittest.TestCase):
    def test_both_castlings_available_when_clear(self):
        board = Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        self.assertIn("e1g1", ucis(board))
        self.assertIn("e1c1", ucis(board))
        board.make_move([m for m in board.legal_moves()
                         if m.uci() == "e1g1"][0])
        self.assertEqual(board.pieces[sq_index("g1")], "K")
        self.assertEqual(board.pieces[sq_index("f1")], "R")
        self.assertNotIn("K", board.castling)
        self.assertNotIn("Q", board.castling)

    def test_black_castling(self):
        board = Board("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1")
        self.assertIn("e8g8", ucis(board))
        self.assertIn("e8c8", ucis(board))

    def test_castling_illegal_through_check(self):
        # Black rook on f8 attacks f1: kingside castling is illegal,
        # queenside is still fine.
        board = Board("r4rk1/8/8/8/8/8/8/R3K2R w KQ - 0 1")
        self.assertNotIn("e1g1", ucis(board))
        self.assertIn("e1c1", ucis(board))

    def test_castling_illegal_while_in_check(self):
        # Black rook on e8 checks the white king: no castling at all.
        board = Board("r3k2r/4r3/8/8/8/8/8/R3K2R w KQkq - 0 1")
        self.assertNotIn("e1g1", ucis(board))
        self.assertNotIn("e1c1", ucis(board))

    def test_castling_rights_lost_after_rook_move(self):
        board = Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        board.make_move([m for m in board.legal_moves()
                         if m.uci() == "h1h2"][0])
        self.assertNotIn("K", board.castling)
        self.assertIn("Q", board.castling)


class TestPromotion(unittest.TestCase):
    def test_pawn_on_7th_generates_four_promotions(self):
        board = Board("8/P7/8/8/8/8/8/4K2k w - - 0 1")
        promos = sorted(m.uci() for m in board.legal_moves()
                        if m.promotion)
        self.assertEqual(promos, ["a7a8b", "a7a8n", "a7a8q", "a7a8r"])

    def test_promotion_places_piece(self):
        board = Board("8/P7/8/8/8/8/8/4K2k w - - 0 1")
        move = [m for m in board.legal_moves() if m.uci() == "a7a8q"][0]
        board.make_move(move)
        self.assertEqual(board.pieces[sq_index("a8")], "Q")


class TestDraws(unittest.TestCase):
    def test_insufficient_material_bare_kings(self):
        board = Board("8/8/4k3/8/8/4K3/8/8 w - - 0 1")
        self.assertTrue(board.insufficient_material())
        self.assertEqual(board.game_status(), "draw")

    def test_insufficient_material_knight(self):
        board = Board("8/8/4k3/8/8/4K1N1/8/8 w - - 0 1")
        self.assertTrue(board.insufficient_material())

    def test_sufficient_material(self):
        board = Board("8/8/4k3/8/8/4K2R/8/8 w - - 0 1")
        self.assertFalse(board.insufficient_material())

    def test_threefold_repetition(self):
        board = Board()
        seq = ["g1f3", "g8f6", "f3g1", "f6g8"]
        for _ in range(2):
            for uci in seq:
                move = [m for m in board.legal_moves() if m.uci() == uci][0]
                board.make_move(move)
        self.assertTrue(board.is_threefold_repetition())
        self.assertEqual(board.game_status(), "draw")

    def test_fifty_move_rule(self):
        board = Board("8/8/4k3/8/8/4K2R/8/8 w - - 99 60")
        self.assertFalse(board.is_fifty_move_draw())
        board.halfmove = 100
        self.assertTrue(board.is_fifty_move_draw())


if __name__ == "__main__":
    unittest.main()
