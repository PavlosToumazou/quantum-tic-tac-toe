import random

class QuantumTicTacToe:
    def __init__(self):
        # Classical marks: 'X', 'O', or None
        self.board_classical = [None] * 9
        # Quantum marks: list of label strings like "X1", "O2" per cell
        self.board_quantum = [[] for _ in range(9)]
        # Moves: move_id -> dict(player, cells=(a,b), status, collapsed_to)
        self.moves = {}
        self.next_move_id = 1
        self.current_player = 'X'

        # Predefined winning lines
        self.lines = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6)
        ]

    # ---------- Basic utilities ----------

    def print_board(self):
        """Pretty-print the board with classical and quantum marks."""
        def cell_str(i):
            if self.board_classical[i] is not None:
                return f" {self.board_classical[i]} "
            if self.board_quantum[i]:
                # Join quantum marks inside the cell
                return ",".join(self.board_quantum[i])[:7].center(7)
            else:
                # Show cell index (1–9) when empty
                return f" {i+1} "

        print("\nCurrent board:")
        for r in range(3):
            row = [cell_str(3*r + c) for c in range(3)]
            print(" | ".join(row))
            if r < 2:
                print("-" * 25)
        print()

    def check_winner(self):
        """Check for a winner based on classical marks."""
        winners = set()
        for a, b, c in self.lines:
            marks = [self.board_classical[a],
                     self.board_classical[b],
                     self.board_classical[c]]
            if marks[0] is not None and marks[0] == marks[1] == marks[2]:
                winners.add(marks[0])

        if len(winners) == 1:
            return winners.pop()   # 'X' or 'O'
        elif len(winners) > 1:
            return "both"          # simultaneous line
        return None

    # ---------- Graph / cycle detection ----------

    def build_graph(self, exclude_move_id=None):
        """
        Build adjacency graph from quantum moves only.
        Returns adjacency dict and edge→move_id map.
        """
        adj = {i: set() for i in range(9)}
        edge_to_move = {}
        for mid, mv in self.moves.items():
            if mv["status"] != "quantum":
                continue
            if exclude_move_id is not None and mid == exclude_move_id:
                continue
            a, b = mv["cells"]
            adj[a].add(b)
            adj[b].add(a)
            edge_to_move[frozenset((a, b))] = mid
        return adj, edge_to_move

    def find_path(self, adj, start, goal):
        """DFS to find any path from start to goal."""
        stack = [(start, [start])]
        visited = set()
        while stack:
            node, path = stack.pop()
            if node == goal:
                return path
            if node in visited:
                continue
            visited.add(node)
            for nb in adj[node]:
                if nb not in visited:
                    stack.append((nb, path + [nb]))
        return None

    def find_cycle_moves(self, new_move_id):
        """
        Check if new_move_id closes a cycle.
        Return set of move_ids in the cycle (including new_move_id) or None.
        """
        mv = self.moves[new_move_id]
        a, b = mv["cells"]
        adj, edge_to_move = self.build_graph(exclude_move_id=new_move_id)

        path = self.find_path(adj, a, b)
        if path is None:
            return None  # no cycle

        cycle_move_ids = set()
        # Edges along the existing path
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            mid = edge_to_move[frozenset((u, v))]
            cycle_move_ids.add(mid)
        # Plus the new move
        cycle_move_ids.add(new_move_id)
        return cycle_move_ids

    # ---------- Collapse mechanics ----------

    def collapse_cycle(self, cycle_move_ids):
        """
        Collapse the moves in the given cycle, then ripple collapse
        other moves affected by newly classical squares.
        """
        # First, collapse the cycle moves
        for mid in sorted(cycle_move_ids):
            mv = self.moves[mid]
            a, b = mv["cells"]
            pl = mv["player"]

            options = []
            for c in (a, b):
                mark = self.board_classical[c]
                if mark is None or mark == pl:
                    options.append(c)

            if not options:
                # Both squares already taken by the opponent in some
                # weird configuration; skip assigning new classical mark.
                mv["status"] = "collapsed"
                mv["collapsed_to"] = None
                continue

            chosen = random.choice(options)
            self.board_classical[chosen] = pl
            mv["status"] = "collapsed"
            mv["collapsed_to"] = chosen

        # Ripple collapse: moves touching a classical cell must collapse too
        changed = True
        while changed:
            changed = False
            for mid, mv in self.moves.items():
                if mv["status"] != "quantum":
                    continue
                a, b = mv["cells"]
                pl = mv["player"]
                a_mark = self.board_classical[a]
                b_mark = self.board_classical[b]

                if a_mark is None and b_mark is None:
                    continue  # no forced collapse yet

                options = []
                for c, mark in ((a, a_mark), (b, b_mark)):
                    if mark is None or mark == pl:
                        options.append(c)

                if not options:
                    # Both endpoints effectively blocked by opponent
                    mv["status"] = "collapsed"
                    mv["collapsed_to"] = None
                    changed = True
                    continue

                chosen = random.choice(options)
                self.board_classical[chosen] = pl
                mv["status"] = "collapsed"
                mv["collapsed_to"] = chosen
                changed = True

        # Rebuild quantum labels on the board from remaining quantum moves
        self.board_quantum = [[] for _ in range(9)]
        for mid, mv in self.moves.items():
            if mv["status"] != "quantum":
                continue
            pl = mv["player"]
            a, b = mv["cells"]
            self.board_quantum[a].append(f"{pl}{mid}")
            self.board_quantum[b].append(f"{pl}{mid}")

    # ---------- Game loop ----------

    def play_turn(self):
        """Handle one turn for the current player."""
        self.print_board()
        print(f"Player {self.current_player}'s turn.")
        print("Choose TWO different non-classical squares (1–9), e.g. '1 5'.")

        while True:
            try:
                raw = input("Your move (i j): ").strip()
                i_str, j_str = raw.split()
                i, j = int(i_str) - 1, int(j_str) - 1
                if i == j:
                    print("Choose two DIFFERENT squares.")
                    continue
                if not (0 <= i <= 8 and 0 <= j <= 8):
                    print("Squares must be between 1 and 9.")
                    continue
                if self.board_classical[i] is not None or self.board_classical[j] is not None:
                    print("You cannot choose a square that already has a classical mark.")
                    continue
                break
            except ValueError:
                print("Please enter two integers like '2 9'.")

        # Register the quantum move
        move_id = self.next_move_id
        self.next_move_id += 1

        self.moves[move_id] = {
            "player": self.current_player,
            "cells": (i, j),
            "status": "quantum",
            "collapsed_to": None
        }

        # Add quantum labels visually
        self.board_quantum[i].append(f"{self.current_player}{move_id}")
        self.board_quantum[j].append(f"{self.current_player}{move_id}")

        # Check for cycle and collapse if needed
        cycle = self.find_cycle_moves(move_id)
        if cycle is not None:
            print("\nA quantum cycle has formed! The board collapses...\n")
            self.collapse_cycle(cycle)

    def play(self):
        """Main loop to play a full game."""
        while True:
            self.play_turn()
            winner = self.check_winner()

            if winner is not None:
                self.print_board()
                if winner == "both":
                    print("Both players completed a line at the same time – quantum draw!")
                else:
                    print(f"Player {winner} wins!")
                break

            # Draw if all squares are classical
            if all(c is not None for c in self.board_classical):
                self.print_board()
                print("The board is full. It's a draw.")
                break

            # Switch player
            self.current_player = 'O' if self.current_player == 'X' else 'X'


if __name__ == "__main__":
    print("=== Quantum Tic-Tac-Toe ===")
    print("Rules (simplified):")
    print("- Each turn you place a quantum mark in TWO different squares.")
    print("- Marks are labeled X1, X2, ... or O1, O2, ...")
    print("- When a cycle of entanglements forms, the board collapses to classical marks.")
    print("- First player to get a classical 3-in-a-row wins.")
    print("- If both get a line at the same time, it's a quantum draw.\n")

    game = QuantumTicTacToe()
    game.play()
