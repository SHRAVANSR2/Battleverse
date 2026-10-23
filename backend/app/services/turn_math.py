"""Pure turn arithmetic. The single source of truth for who speaks when."""

from __future__ import annotations


def round_for_turn(turn_number: int) -> int:
    """1-based turn -> 1-based round. Turn 1 and 2 are round 1."""
    if turn_number < 1:
        raise ValueError("turn_number is 1-based")
    return (turn_number - 1) // 2 + 1


def speaker_is_a(turn_number: int) -> bool:
    """A opens each round (odd turns); B replies (even turns)."""
    if turn_number < 1:
        raise ValueError("turn_number is 1-based")
    return turn_number % 2 == 1


def total_turns(round_count: int) -> int:
    if round_count < 1:
        raise ValueError("round_count must be at least 1")
    return round_count * 2


def is_final_turn(turn_number: int, round_count: int) -> bool:
    return turn_number >= total_turns(round_count)