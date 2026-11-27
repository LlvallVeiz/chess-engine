"""Perft (move-count) verification against known reference positions.

Reference counts are the standard ones from the Chess Programming Wiki
perft suite:
- Start position: depth 1-4 = 20, 400, 8902, 197281.
- Kiwipete:       depth 1-3 = 48, 2039, 97862.
"""

import unittest

from chess_engine.board import Board

KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"


class TestPerftStartPosition(unittest.TestCase):
    def test_depth1(self):
        self.assertEqual(Board().perft(1), 20)

    def test_depth2(self):
        self.assertEqual(Board().perft(2), 400)

    def test_depth3(self):
        self.assertEqual(Board().perft(3), 8902)

    def test_depth4(self):
        self.assertEqual(Board().perft(4), 197281)


class TestPerftKiwipete(unittest.TestCase):
    def test_depth1(self):
        self.assertEqual(Board(KIWIPETE).perft(1), 48)

    def test_depth2(self):
        self.assertEqual(Board(KIWIPETE).perft(2), 2039)

    def test_depth3(self):
        self.assertEqual(Board(KIWIPETE).perft(3), 97862)


if __name__ == "__main__":
    unittest.main()
