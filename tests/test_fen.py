"""FEN round-trip tests."""

import unittest

from chess_engine.board import Board, START_FEN

POSITIONS = [
    START_FEN,
    # Kiwipete.
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    # Castling rights + en passant square + clocks.
    "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2",
    # Mid-game, black to move, partial castling rights.
    "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
    # Endgame, no castling.
    "8/5k2/3p4/1p1Pp2p/pP2Pp1P/P4P1K/8/8 b - - 0 50",
]


class TestFenRoundTrip(unittest.TestCase):
    def test_parse_then_generate(self):
        for fen in POSITIONS:
            board = Board(fen)
            self.assertEqual(board.fen(), fen, "round-trip failed for %s" % fen)

    def test_start_position_fields(self):
        board = Board()
        self.assertEqual(board.turn, "w")
        self.assertEqual(board.castling, "KQkq")
        self.assertIsNone(board.ep_square)
        self.assertEqual(board.halfmove, 0)
        self.assertEqual(board.fullmove, 1)

    def test_invalid_fen_rejected(self):
        with self.assertRaises(ValueError):
            Board("not a fen")
        with self.assertRaises(ValueError):
            Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR x KQkq - 0 1")
        with self.assertRaises(ValueError):
            Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0")


if __name__ == "__main__":
    unittest.main()
