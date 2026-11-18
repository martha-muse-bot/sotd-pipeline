import re
from pathlib import Path

import pytest

from sotd.match.blade_matcher import BladeMatcher


class TestBladeFormatMatchingDebug:
    """Debug tests for blade format matching issues."""

    @pytest.fixture
    def blade_matcher(self):
        """Create a blade matcher instance for testing with mock catalog."""
        catalog_path = Path("tests/match/test_blade_catalog.yaml")
        return BladeMatcher(catalog_path=catalog_path)

    def test_personna_hair_shaper_with_shavette_context(self, blade_matcher):
        """
        Test that "Personna hair shaper" gets matched to "Hair Shaper" format
        when the razor is a "Shavette" format.

        This reproduces the issue from the matched data where:
        - Razor: "Dovo shavette" (format: "Shavette")
        - Blade: "Personna hair shaper"
        - Expected: Should match to "Hair Shaper" format
        - Actual: Was matching to "Injector" format
        """
        # Test input matching the real scenario
        blade_text = "Personna hair shaper"
        razor_format = "Shavette"  # This should map to "Hair Shaper" blade format

        # Use match_with_context to get the intelligent format decision
        result = blade_matcher.match_with_context(
            normalized_text=blade_text, razor_format=razor_format, original_text=blade_text
        )

        print("\n=== Debug Output ===")
        print(f"Blade text: {blade_text}")
        print(f"Razor format: {razor_format}")
        print(f"Result: {result}")

        if result.matched:
            print(f"Matched brand: {result.matched.get('brand')}")
            print(f"Matched model: {result.matched.get('model')}")
            print(f"Matched format: {result.matched.get('format')}")
            print(f"Match type: {result.match_type}")
            print(f"Pattern: {result.pattern}")
        else:
            print("No match found")

        # The blade should be matched to Hair Shaper format, not Injector
        assert result.matched is not None, "Blade should be matched"
        expected_format = "Hair Shaper"
        actual_format = result.matched.get("format")
        assert (
            actual_format == expected_format
        ), f"Expected '{expected_format}' format, got '{actual_format}'"

        expected_brand = "Personna"
        actual_brand = result.matched.get("brand")
        assert (
            actual_brand == expected_brand
        ), f"Expected '{expected_brand}' brand, got '{actual_brand}'"

        expected_model = "Hair Shaper"
        actual_model = result.matched.get("model")
        assert (
            actual_model == expected_model
        ), f"Expected '{expected_model}' model, got '{actual_model}'"

    def test_personna_hair_shaper_without_context(self, blade_matcher):
        """
        Test that "Personna hair shaper" gets matched correctly even without razor context.
        This should still match to "Hair Shaper" format based on pattern specificity.
        """
        blade_text = "Personna hair shaper"

        # Use basic match without context
        result = blade_matcher.match(value=blade_text, original=blade_text)

        print("\n=== Debug Output (No Context) ===")
        print(f"Blade text: {blade_text}")
        print(f"Result: {result}")

        if result.matched:
            print(f"Matched brand: {result.matched.get('brand')}")
            print(f"Matched model: {result.matched.get('model')}")
            print(f"Matched format: {result.matched.get('format')}")
            print(f"Match type: {result.match_type}")
            print(f"Pattern: {result.pattern}")
        else:
            print("No match found")

        # Should still match to Hair Shaper format
        assert result.matched is not None, "Blade should be matched"
        # The catalog correctly maps "Personna hair shaper" to "Hair Shaper" format
        expected_format = "Hair Shaper"  # This is the correct expected behavior
        actual_format = result.matched.get("format")
        assert (
            actual_format == expected_format
        ), f"Expected '{expected_format}' format, got '{actual_format}'"

    def test_pattern_priority_debug(self, blade_matcher):
        """
        Debug the pattern priority to see which patterns are being tried first.
        """
        print("\n=== Pattern Priority Debug ===")

        # Look at the compiled patterns for Personna
        personna_patterns = []
        for brand, model, fmt, pattern, compiled, entry in blade_matcher.patterns:
            if brand.lower() == "personna":
                personna_patterns.append(
                    {
                        "brand": brand,
                        "model": model,
                        "format": fmt,
                        "pattern": pattern,
                        "length": len(pattern),
                    }
                )

        # Sort by length to see priority
        personna_patterns.sort(key=lambda x: x["length"], reverse=True)

        print("Personna patterns sorted by length (longest first):")
        for p in personna_patterns:
            print(f"  {p['format']}: {p['pattern']} (length: {p['length']})")

        # Check if Hair Shaper pattern exists and its priority
        hair_shaper_patterns = [p for p in personna_patterns if p["format"] == "Hair Shaper"]
        injector_patterns = [p for p in personna_patterns if p["format"] == "Injector"]

        print(f"\nHair Shaper patterns: {len(hair_shaper_patterns)}")
        print(f"Injector patterns: {len(injector_patterns)}")

        if hair_shaper_patterns:
            best_hair = hair_shaper_patterns[0]
            print(
                f"Best Hair Shaper pattern: {best_hair['pattern']} "
                f"(length: {best_hair['length']})"
            )
        if injector_patterns:
            best_injector = injector_patterns[0]
            print(
                f"Best Injector pattern: {best_injector['pattern']} "
                f"(length: {best_injector['length']})"
            )

    def test_regex_matching_debug(self, blade_matcher):
        """
        Test the actual regex patterns to see which one matches "Personna hair shaper".
        """
        blade_text = "Personna hair shaper"

        print("\n=== Regex Matching Debug ===")
        print(f"Testing text: '{blade_text}'")

        # Test each Personna pattern manually
        for brand, model, fmt, pattern, compiled, entry in blade_matcher.patterns:
            if brand.lower() == "personna":
                match = compiled.search(blade_text)
                if match:
                    print(f"✓ MATCH: {fmt} - {pattern}")
                    print(f"  Brand: {brand}, Model: {model}")
                    print(f"  Match span: {match.span()}")
                    start, end = match.span()
                    matched_text = blade_text[start:end]
                    print(f"  Matched text: '{matched_text}'")
                else:
                    print(f"✗ NO MATCH: {fmt} - {pattern}")

        # Now test the specific patterns we're concerned about
        print("\n=== Specific Pattern Testing ===")

        # Test Hair Shaper pattern
        hair_shaper_pattern = "person+a.*hair.*shaper"
        hair_shaper_regex = re.compile(hair_shaper_pattern, re.IGNORECASE)
        hair_shaper_match = hair_shaper_regex.search(blade_text)
        hair_result = "✓ MATCH" if hair_shaper_match else "✗ NO MATCH"
        print(f"Hair Shaper pattern '{hair_shaper_pattern}': {hair_result}")

        # Test Injector pattern
        injector_pattern = "person+a(?:.*inject)?"
        injector_regex = re.compile(injector_pattern, re.IGNORECASE)
        injector_match = injector_regex.search(blade_text)
        injector_result = "✓ MATCH" if injector_match else "✗ NO MATCH"
        print(f"Injector pattern '{injector_pattern}': {injector_result}")

        # Show why the injector pattern matches
        if injector_match:
            print("  Injector pattern matches because:")
            print("    - 'person+a' matches 'Personna'")
            print("    - '(?:.*inject)?' is optional and doesn't require 'inject'")
            print("    - So 'Personna hair shaper' matches even without 'inject'")

    def test_shavette_format_mapping_debug(self, blade_matcher):
        """
        Debug what target blade format is determined for different razor formats.
        """
        print("\n=== Shavette Format Mapping Debug ===")

        test_formats = [
            "Shavette",
            "shavette",
            "SHAVETTE",
            "Shavette (Hair Shaper)",
            "shavette (hair shaper)",
            "SHAVETTE (HAIR SHAPER)",
            "Shavette (AC)",
            "Shavette (GEM)",
            "Shavette (Injector)",
        ]

        for razor_format in test_formats:
            target_format = blade_matcher._get_target_blade_format(razor_format)
            print(f"Razor format: '{razor_format}' -> Target blade format: '{target_format}'")

        # Test the specific case from our data
        razor_format = "Shavette"  # This is what we get from the matched data
        target_format = blade_matcher._get_target_blade_format(razor_format)
        print("\nOur case:")
        print(f"Razor format: '{razor_format}' -> Target blade format: '{target_format}'")

        # Check if this target format exists in the blade catalog
        if target_format in blade_matcher.catalog:
            print(f"✓ Target format '{target_format}' exists in blade catalog")
            brands = list(blade_matcher.catalog[target_format].keys())
            print(f"  Available brands: {brands}")
        else:
            print(f"✗ Target format '{target_format}' does NOT exist in blade catalog")
            print(f"  Available formats: {list(blade_matcher.catalog.keys())}")

        # This explains why the fallback system is being used
        print(f"\nSince '{target_format}' is not in the catalog, the system falls back to")
        print("the general fallback system which uses basic pattern matching instead of")
        print("context-aware format-specific matching.")

    def test_fix_verification(self, blade_matcher):
        """
        Test that after the fix, "Personna hair shaper" with "Shavette" razor
        correctly maps to "Hair Shaper" format.
        """
        print("\n=== Fix Verification Test ===")

        # First, let's manually fix the mapping for this test
        # In the real fix, we'd update _get_target_blade_format method
        original_mapping = blade_matcher._get_target_blade_format

        def fixed_mapping(razor_format):
            """Fixed mapping that handles generic 'Shavette' format."""
            if razor_format.lower() == "shavette":
                return "Hair Shaper"  # Generic shavettes typically use hair shaper blades
            return original_mapping(razor_format)

        # Temporarily replace the method for testing
        blade_matcher._get_target_blade_format = fixed_mapping

        try:
            # Test the fixed mapping
            razor_format = "Shavette"
            target_format = blade_matcher._get_target_blade_format(razor_format)
            print(f"Fixed mapping: '{razor_format}' -> '{target_format}'")

            # Verify the target format exists in catalog
            assert (
                target_format in blade_matcher.catalog
            ), f"Target format '{target_format}' should exist in catalog"
            print(f"✓ Target format '{target_format}' exists in blade catalog")

            # Now test the actual blade matching
            blade_text = "Personna hair shaper"
            result = blade_matcher.match_with_context(
                normalized_text=blade_text, razor_format=razor_format, original_text=blade_text
            )

            print("\nBlade matching result:")
            print(f"  Blade: {blade_text}")
            print(f"  Razor: {razor_format}")
            print(f"  Target format: {target_format}")
            print(f"  Result: {result}")

            if result.matched:
                print(f"  Matched format: {result.matched.get('format')}")
                print(f"  Matched model: {result.matched.get('model')}")

            # The blade should now be matched to Hair Shaper format
            assert result.matched is not None, "Blade should be matched"
            assert (
                result.matched.get("format") == "Hair Shaper"
            ), f"Expected 'Hair Shaper' format, got '{result.matched.get('format')}'"
            print("✓ SUCCESS: Blade correctly matched to Hair Shaper format!")

        finally:
            # Restore original method
            blade_matcher._get_target_blade_format = original_mapping

    def test_pattern_fallback_order_debug(self, blade_matcher):
        """
        Debug the pattern fallback order to see if there's a default order
        that's overriding the length-based sorting.
        """
        print("\n=== Pattern Fallback Order Debug ===")

        # Let's see what the actual self.patterns array looks like
        print("First 10 patterns in self.patterns array:")
        for i, (brand, model, fmt, pattern, compiled, entry) in enumerate(
            blade_matcher.patterns[:10]
        ):
            print(f"  {i}: {fmt} - {pattern} (length: {len(pattern)})")

        # Check if patterns are actually sorted by length
        print("\nChecking if patterns are sorted by length:")
        lengths = [
            len(pattern)
            for brand, model, fmt, pattern, compiled, entry in blade_matcher.patterns[:20]
        ]
        print(f"First 20 pattern lengths: {lengths}")

        # Check if they're in descending order (longest first)
        is_sorted = all(lengths[i] >= lengths[i + 1] for i in range(len(lengths) - 1))
        print(f"Patterns are sorted by length (descending): {is_sorted}")

        # Look specifically at Personna patterns in the actual array order
        print("\nPersonna patterns in actual array order:")
        personna_in_order = []
        for i, (brand, model, fmt, pattern, compiled, entry) in enumerate(blade_matcher.patterns):
            if brand.lower() == "personna":
                personna_in_order.append(
                    {"index": i, "format": fmt, "pattern": pattern, "length": len(pattern)}
                )

        for p in personna_in_order:
            print(f"  Index {p['index']}: {p['format']} - {p['pattern']} (length: {p['length']})")

        # Check if there's a specific order for formats
        print("\nChecking format order in patterns array:")
        format_order = []
        seen_formats = set()
        for brand, model, fmt, pattern, compiled, entry in blade_matcher.patterns:
            if fmt not in seen_formats:
                format_order.append(fmt)
                seen_formats.add(fmt)
            if len(format_order) >= 10:  # Just show first 10
                break

        print(f"Format order in patterns array: {format_order}")

        # Now let's simulate what happens in the basic fallback
        print("\n=== Simulating Basic Fallback ===")
        blade_text = "Personna hair shaper"

        # Simulate the basic pattern matching loop
        print("Simulating pattern matching loop:")
        for i, (brand, model, fmt, raw_pattern, compiled, entry) in enumerate(
            blade_matcher.patterns
        ):
            if brand.lower() == "personna":
                match = compiled.search(blade_text)
                if match:
                    print(f"  ✓ MATCH at index {i}: {fmt} - {raw_pattern}")
                    print(f"    Brand: {brand}, Model: {model}")
                    print("    This pattern wins and returns early!")
                    break
                else:
                    print(f"  ✗ NO MATCH at index {i}: {fmt} - {raw_pattern}")

        # This should show us exactly which pattern is being tried first and winning

    def test_match_with_context_debug_trace(self, blade_matcher):
        """
        Add debug logging to match_with_context method to trace through
        the execution step by step and see where the Injector pattern is coming from.
        """
        print("\n=== Match With Context Debug Trace ===")

        # Store original methods to restore later
        original_collect_correct = blade_matcher._collect_correct_matches_in_format
        original_match_regex = blade_matcher._match_regex_in_format
        original_build_fallback = blade_matcher._build_fallback_formats

        try:
            # Add debug logging to key methods
            def debug_collect_correct_matches(value, target_format):
                print(f"  [DEBUG] _collect_correct_matches_in_format('{value}', '{target_format}')")
                result = original_collect_correct(value, target_format)
                print(f"  [DEBUG] Result: {len(result) if result else 0} matches")
                return result

            def debug_match_regex_in_format(normalized_value, target_format, is_shavette):
                print(
                    f"  [DEBUG] _match_regex_in_format('{normalized_value}', '{target_format}', {is_shavette})"
                )
                result = original_match_regex(normalized_value, target_format, is_shavette)
                if result:
                    print(
                        f"  [DEBUG] Regex match found: {result['matched']['format']} - {result['matched']['model']}"
                    )
                else:
                    print("  [DEBUG] No regex match found")
                return result

            def debug_build_fallback_formats(target_format):
                print(f"  [DEBUG] _build_fallback_formats('{target_format}')")
                result = original_build_fallback(target_format)
                print(f"  [DEBUG] Fallback formats: {result}")
                return result

            # Replace methods with debug versions
            blade_matcher._collect_correct_matches_in_format = debug_collect_correct_matches
            blade_matcher._match_regex_in_format = debug_match_regex_in_format
            blade_matcher._build_fallback_formats = debug_build_fallback_formats

            # Now test the actual match_with_context method
            blade_text = "Personna hair shaper"
            razor_format = "Shavette"

            print(f"Calling match_with_context('{blade_text}', '{razor_format}')")
            print("=" * 60)

            result = blade_matcher.match_with_context(
                normalized_text=blade_text, razor_format=razor_format, original_text=blade_text
            )

            print("=" * 60)
            print(f"Final result: {result}")
            if result.matched:
                print(f"  Format: {result.matched.get('format')}")
                print(f"  Model: {result.matched.get('model')}")
                print(f"  Pattern: {result.pattern}")

            # This should show us exactly which path was taken and where the Injector pattern came from

        finally:
            # Restore original methods
            blade_matcher._collect_correct_matches_in_format = original_collect_correct
            blade_matcher._match_regex_in_format = original_match_regex
            blade_matcher._build_fallback_formats = original_build_fallback

    def test_fallback_format_debug(self, blade_matcher):
        """
        Debug the fallback format building process to see why Injector is being
        tried before Hair Shaper.
        """
        print("\n=== Fallback Format Debug ===")

        # Test the fallback format building for different target formats
        test_formats = ["Shavette", "Hair Shaper", "Injector", "DE"]

        for target_format in test_formats:
            print(f"\n--- Target Format: {target_format} ---")

            # Check if it exists in catalog
            if target_format in blade_matcher.catalog:
                print("  ✓ Exists in catalog")
                brands = list(blade_matcher.catalog[target_format].keys())
                print(f"  Available brands: {brands}")
            else:
                print("  ✗ Does NOT exist in catalog")

            # Build fallback formats
            fallback_formats = blade_matcher._build_fallback_formats(target_format)
            print(f"  Fallback formats: {fallback_formats}")

            # Check if this is a Shavette razor
            is_shavette = target_format.upper().startswith("SHAVETTE")
            print(f"  Is Shavette: {is_shavette}")

            # Build Shavette-specific fallback if applicable
            if is_shavette:
                shavette_fallbacks = blade_matcher._build_shavette_fallback_formats(target_format)
                print(f"  Shavette fallback formats: {shavette_fallbacks}")

        # Now let's trace through the actual fallback logic in match_with_context
        print("\n=== Tracing Fallback Logic ===")

        # Store original methods
        original_build_shavette = blade_matcher._build_shavette_fallback_formats

        def debug_build_shavette_fallback_formats(target_format):
            print(f"  [DEBUG] _build_shavette_fallback_formats('{target_format}')")
            result = original_build_shavette(target_format)
            print(f"  [DEBUG] Shavette fallback result: {result}")
            return result

        try:
            blade_matcher._build_shavette_fallback_formats = debug_build_shavette_fallback_formats

            # Test the actual fallback logic
            blade_text = "Personna hair shaper"
            razor_format = "Shavette"

            print("\nCalling match_with_context with enhanced debug...")
            print("=" * 60)

            result = blade_matcher.match_with_context(
                normalized_text=blade_text, razor_format=razor_format, original_text=blade_text
            )

            print("=" * 60)
            print(f"Final result: {result}")

        finally:
            # Restore original method
            blade_matcher._build_shavette_fallback_formats = original_build_shavette
