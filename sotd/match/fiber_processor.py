import re
from typing import Optional


class FiberProcessor:
    """Fiber processing logic for brush matching."""

    def __init__(self):
        """Initialize the fiber processor."""
        # Comprehensive fiber patterns for detection
        self._fiber_patterns = {
            "Synthetic": (
                r"(acrylic|timber|tux|mew|silk|synt|synbad|2bed|captain|cashmere|"
                r"faux.*horse|black.*(magic|wolf)|g4|boss|st-?(1|2)|trafalgar\s*t[23]|"
                r"\bt[23]\b|kong|hi\s*brush|ak47|g5[abc]|stf|quartermoon|fibre|"
                r"\bmig\b|synthetic badger|motherlode|nylon|plissoft|tuxedo)"
            ),
            "Mixed Badger/Boar": r"(mix|mixed|mi[sx]tura?|badg.*boar|boar.*badg|fusion)",
            "Boar": r"\b(boar|shoat)\b",
            "Badger": (
                r"(hmw|high.*mo|(2|3|two|three)\s*band|shd|badger|silvertip|super|"
                r"gelo|gelous|gelousy|finest|best|ultralux|fanchurian|\blod\b)"
            ),
            "Horse": r"\bhorse(hair)?\b",
        }

    def match_fiber(self, text: str) -> Optional[str]:
        """Match fiber type from text using comprehensive patterns."""
        if not text:
            return None

        for fiber, pattern in self._fiber_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return fiber
        return None

    def process_fiber_info(self, value: str, match_dict: dict) -> None:
        """Process fiber information from the input value and update match dictionary."""
        user_fiber = self.match_fiber(value)

        if user_fiber:
            if match_dict.get("fiber") and match_dict["fiber"].lower() == user_fiber.lower():
                match_dict["fiber_strategy"] = "user_input"
            elif match_dict.get("fiber") and match_dict["fiber"].lower() != user_fiber.lower():
                match_dict["fiber_conflict"] = user_fiber
                match_dict["fiber_strategy"] = "yaml"
            else:
                match_dict["fiber"] = user_fiber
                match_dict["fiber_strategy"] = "user_input"
        else:
            if match_dict.get("fiber_strategy") is None:
                match_dict["fiber_strategy"] = "default" if "default" in value.lower() else "yaml"

    def resolve_fiber(self, updated: dict, parsed_fiber: str | None) -> None:
        """Resolve fiber information in the match result."""
        if "fiber_strategy" not in updated:
            fiber = updated.get("fiber")
            default_fiber = updated.get("default fiber")
            if fiber:
                updated["fiber_strategy"] = "yaml"
                if parsed_fiber and parsed_fiber.lower() != fiber.lower():
                    updated["fiber_conflict"] = f"user_input: {parsed_fiber}"
            elif parsed_fiber:
                updated["fiber"] = parsed_fiber
                updated["fiber_strategy"] = "user_input"
            elif default_fiber:
                updated["fiber"] = default_fiber
                updated["fiber_strategy"] = "default"
            else:
                updated["fiber_strategy"] = "unset"

    def find_fiber_word_indices(
        self, words: list[str], fiber_start: int, fiber_end: int
    ) -> list[int]:
        """Find indices of words that contain fiber information."""
        fiber_indices = []
        for i, word in enumerate(words):
            if fiber_start <= i <= fiber_end:
                fiber_indices.append(i)
        return fiber_indices

    def extract_fiber_from_text(self, text: str) -> Optional[str]:
        """Extract fiber type from text using comprehensive patterns."""
        return self.match_fiber(text)

    def validate_fiber_strategy(self, fiber_strategy: str) -> bool:
        """Validate that a fiber strategy is valid."""
        valid_strategies = {"user_input", "yaml", "default", "unset"}
        return fiber_strategy in valid_strategies

    def get_fiber_patterns(self) -> dict[str, str]:
        """Get the fiber patterns used for matching."""
        return self._fiber_patterns.copy()
