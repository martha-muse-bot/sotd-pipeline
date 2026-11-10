from sotd.extract.comment import parse_comment


def test_parse_comment_all_fields():
    comment = {
        "body": "\n".join(
            [
                "* **Razor:** Blackbird",
                "* **Blade:** Feather",
                "* **Brush:** Simpson",
                "* **Soap:** Tabac",
            ]
        )
    }
    ss = parse_comment(comment)
    assert ss == {
        "body": (
            "* **Razor:** Blackbird\n"
            "* **Blade:** Feather\n"
            "* **Brush:** Simpson\n"
            "* **Soap:** Tabac"
        ),
        "razor": {"original": "Blackbird", "normalized": "Blackbird"},
        "blade": {"original": "Feather", "normalized": "Feather"},
        "brush": {"original": "Simpson", "normalized": "Simpson"},
        "soap": {"original": "Tabac", "normalized": "Tabac"},
    }


def test_parse_comment_partial():
    comment = {"body": "\n".join(["* **Brush:** Omega", "* **Soap:** Cella"])}
    assert parse_comment(comment) == {
        "body": "* **Brush:** Omega\n* **Soap:** Cella",
        "brush": {"original": "Omega", "normalized": "Omega"},
        "soap": {"original": "Cella", "normalized": "Cella"},
    }


def test_parse_comment_none():
    comment = {"body": "Great shave today, no product mentioned."}
    assert parse_comment(comment) is None


def test_parse_comment_mixed_lines():
    comment = {
        "body": "\n".join(
            [
                "* **Razor:** Game Changer",
                "Blade: Nacet",  # invalid
                "* **Blade:** Nacet",
                "* **Blade:** Feather",  # should be ignored
                "* **Soap:** Arko",
            ]
        )
    }
    assert parse_comment(comment) == {
        "body": (
            "* **Razor:** Game Changer\n"
            "Blade: Nacet\n"
            "* **Blade:** Nacet\n"
            "* **Blade:** Feather\n"
            "* **Soap:** Arko"
        ),
        "razor": {"original": "Game Changer", "normalized": "Game Changer"},
        "blade": {"original": "Nacet", "normalized": "Nacet"},
        "soap": {"original": "Arko", "normalized": "Arko"},
    }


def test_parse_comment_key_order():
    comment = {
        "author": "test_user",
        "body": (
            "* **Razor:** Blackbird\n"
            "* **Blade:** Feather\n"
            "* **Brush:** Simpson\n"
            "* **Soap:** Tabac"
        ),
        "created_utc": "2025-04-01T08:00:00Z",
        "id": "abc123",
        "thread_id": "thread456",
        "thread_title": "Example Title",
        "url": "https://example.com",
    }
    result = parse_comment(comment)
    assert result is not None, "parse_comment returned None"
    keys = list(result.keys())
    assert keys[:7] == [
        "author",
        "body",
        "created_utc",
        "id",
        "thread_id",
        "thread_title",
        "url",
    ], "Comment metadata keys missing or out of order"
    assert keys[7:] == ["razor", "blade", "brush", "soap"], "Extracted keys missing or out of order"


def test_parse_comment_with_markdown_links():
    comment = {
        "body": "\n".join(
            [
                "* **Razor:** [Blackland Blackbird](https://example.com/razor)",
                "* **Blade:** [Feather](https://example.com/blade)",
                "* **Brush:** [Simpson](https://example.com/brush)",
                "* **Soap:** [Tabac](https://example.com/soap)",
            ]
        )
    }
    assert parse_comment(comment) == {
        "body": (
            "* **Razor:** [Blackland Blackbird](https://example.com/razor)\n"
            "* **Blade:** [Feather](https://example.com/blade)\n"
            "* **Brush:** [Simpson](https://example.com/brush)\n"
            "* **Soap:** [Tabac](https://example.com/soap)"
        ),
        "razor": {"original": "Blackland Blackbird", "normalized": "Blackland Blackbird"},
        "blade": {"original": "Feather", "normalized": "Feather"},
        "brush": {"original": "Simpson", "normalized": "Simpson"},
        "soap": {"original": "Tabac", "normalized": "Tabac"},
    }


def test_parse_comment_with_competition_tags():
    """Test that competition tags are normalized correctly."""
    comment = {
        "body": "\n".join(
            [
                "* **Razor:** Blackbird $DOORKNOB",
                "* **Blade:** Feather (3x)",
                "* **Brush:** Simpson",
                "* **Soap:** Tabac (sample)",
            ]
        )
    }
    result = parse_comment(comment)
    assert result == {
        "body": (
            "* **Razor:** Blackbird $DOORKNOB\n"
            "* **Blade:** Feather (3x)\n"
            "* **Brush:** Simpson\n"
            "* **Soap:** Tabac (sample)"
        ),
        "razor": {"original": "Blackbird $DOORKNOB", "normalized": "Blackbird"},
        "blade": {"original": "Feather (3x)", "normalized": "Feather"},
        "brush": {"original": "Simpson", "normalized": "Simpson"},
        "soap": {"original": "Tabac (sample)", "normalized": "Tabac"},
    }


def test_parse_comment_with_usage_counts():
    """Test that usage counts are normalized correctly."""
    comment = {
        "body": "\n".join(
            [
                "* **Razor:** Karve Overlander Nickel Plated Brass w/ 90mm Overlander handle",
                "* **Blade:** Gillette Nacet (5)",
                "* **Brush:** Elite handle w/ Declaration knot",
                "* **Soap:** Barrister and Mann Seville",
            ]
        )
    }
    result = parse_comment(comment)
    assert result == {
        "body": (
            "* **Razor:** Karve Overlander Nickel Plated Brass w/ 90mm Overlander handle\n"
            "* **Blade:** Gillette Nacet (5)\n"
            "* **Brush:** Elite handle w/ Declaration knot\n"
            "* **Soap:** Barrister and Mann Seville"
        ),
        "razor": {
            "original": "Karve Overlander Nickel Plated Brass w/ 90mm Overlander handle",
            "normalized": "Karve Overlander Nickel Plated Brass w/ 90mm Overlander handle",
        },
        "blade": {"original": "Gillette Nacet (5)", "normalized": "Gillette Nacet"},
        "brush": {
            "original": "Elite handle w/ Declaration knot",
            "normalized": "Elite handle w/ Declaration knot",
        },
        "soap": {
            "original": "Barrister and Mann Seville",
            "normalized": "Barrister and Mann Seville",
        },
    }


def test_parse_comment_with_special_characters():
    """Test that special characters are handled correctly."""
    comment = {
        "body": "\n".join(
            [
                "* **Razor:** Merkur 37c $ZAMAC $SLANT",
                "* **Blade:** Personna Blue (new)",
                "* **Brush:** Omega 10049",
                "* **Soap:** Stirling Soap Co. Executive Man",
            ]
        )
    }
    result = parse_comment(comment)
    assert result == {
        "body": (
            "* **Razor:** Merkur 37c $ZAMAC $SLANT\n"
            "* **Blade:** Personna Blue (new)\n"
            "* **Brush:** Omega 10049\n"
            "* **Soap:** Stirling Soap Co. Executive Man"
        ),
        "razor": {"original": "Merkur 37c $ZAMAC $SLANT", "normalized": "Merkur 37c"},
        "blade": {"original": "Personna Blue (new)", "normalized": "Personna Blue"},
        "brush": {"original": "Omega 10049", "normalized": "Omega 10049"},
        "soap": {
            "original": "Stirling Soap Co. Executive Man",
            "normalized": "Stirling Soap Co. Executive Man",
        },
    }


def test_parse_comment_empty_strings():
    """Test that empty strings are handled correctly."""
    comment = {
        "body": "\n".join(
            [
                "* **Razor:** ",
                "* **Blade:** Feather",
                "* **Brush:** ",
                "* **Soap:** Tabac",
            ]
        )
    }
    result = parse_comment(comment)
    # Should only include fields that have actual values (empty fields are excluded)
    assert result == {
        "body": ("* **Razor:**\n" "* **Blade:** Feather\n" "* **Brush:**\n" "* **Soap:** Tabac"),
        "blade": {"original": "Feather", "normalized": "Feather"},
        "soap": {"original": "Tabac", "normalized": "Tabac"},
    }


def test_parse_comment_razor_test_exclusion():
    """Test that 'Razor Test' lines are excluded and actual 'Razor:' lines are extracted."""
    # Simulate the exact comment from 2025-07 that had the bug
    comment = {
        "body": "\n".join(
            [
                "Monday 7/28 Shave",
                "",
                "GEM JULY",
                "",
                "MDC MONDAY",
                "",
                "MICROMATIC MONDAY",
                "",
                "",
                "",
                "Razor Test - Received Edge with CrOx Stropping",
                "",
                "It shaved OK on WTG and Across the Chin",
                "",
                "Against the Grain was a bit tuggy",
                "",
                "It's to the stones for a Bevel set",
                "",
                "GEM Bullet Tip took it to a nice BBS result",
                "",
                "",
                "",
                'Razor: Portland Cutlery Steinmetz "Salamander"',
                "",
                "Blade: Original Edge Stropped on Green CrOx",
                "",
                "Clean Up: GEM MicroMatic Bullet Point",
                "",
                "Lather: Martin de Candre Absinthe Sample",
                "",
                "Brush: Stirling PRO Synthetic",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert "razor" in result
    # Should extract the correct razor, not the "Razor Test" line
    assert result["razor"]["original"] == 'Portland Cutlery Steinmetz "Salamander"'
    assert result["razor"]["normalized"] == 'Portland Cutlery Steinmetz "Salamander"'


def test_parse_comment_razor_test_exclusion_2025_06():
    """Test the other affected comment from 2025-06."""
    comment = {
        "body": "\n".join(
            [
                "Sunday 6/22 Shave",
                "",
                "",
                "",
                "Razor Test - 20 Laps on Green CrOx - 50 on Leather",
                "",
                "Not too bad but probably needs a bevel set",
                "",
                "It will eventually turn out to be a cute little shaver",
                "",
                "Parker Semi Slant finished up in one pass",
                "",
                "Overall a pretty decent BBS Sunday shave",
                "",
                "",
                "",
                "Razor: Lee Manufacturing Co. - Lee's Warranted",
                "",
                "Blade: Carbon Steel",
                "",
                "Clean Up: Parker Semi-Slant",
                "",
                "Lather: Abbate Y La Mantia Blue Tobacco",
                "",
                "Brush: Ever-Ready Vintage 150 Boar Knot",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert "razor" in result
    # Should extract the correct razor, not the "Razor Test" line
    assert result["razor"]["original"] == "Lee Manufacturing Co. - Lee's Warranted"
    assert result["razor"]["normalized"] == "Lee Manufacturing Co. - Lee's Warranted"


def test_parse_comment_pattern_priority_narrative_vs_explicit():
    """Test that explicit markers win over ambiguous patterns, even when ambiguous appears first."""
    # This tests the specific case where narrative text matches ambiguous pattern
    # but explicit marker on later line should win
    comment = {
        "body": "\n".join(
            [
                "Wednesday 7/16 Shave",
                "",
                "GEM JULY",
                "",
                "WECK WEDNESDAY",
                "",
                "",
                "",
                "Personna Blade on it's 15th use - binned after shave",
                "",
                "Razor was still smooth but was not effective cutter",
                "",
                "Treet razor with PAL Carbon Steel blade cleaned up well",
                "",
                "Overall an acceptable BBS shave result",
                "",
                "",
                "",
                "Razor: WECK Hair Shaper - Pink Scales",
                "",
                "Blade: Personna Hair Shaper (15X)",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert "razor" in result
    # Should extract the explicit marker line, not the narrative text
    assert result["razor"]["original"] == "WECK Hair Shaper - Pink Scales"
    assert result["razor"]["normalized"] == "WECK Hair Shaper - Pink Scales"


def test_parse_comment_soap_explicit_lather_wins_over_ambiguous_soap():
    """Test that explicit 'Lather:' pattern wins over ambiguous 'Soap' pattern."""
    # This tests the specific case from comment id ntmpg39 where
    # "* **Lather:** Mickey Lee Soapworks - The Kraken - Soap" should win over "Soap kill."
    comment = {
        "body": "\n".join(
            [
                "* **Brush:** Yaqi - 24mm Boar",
                "* **Razor:** Schick - Type I2 (Hydro-Magic)",
                "* **Blade:** Personna - 74 - Injector (70)",
                "* **Lather:** Mickey Lee Soapworks - The Kraken - Soap",
                "* **Post Shave:** House of Mammoth - Sonder - Aftershave",
                "* **Fragrance:** House of Mammoth - Sandalorian - Eau de Parfum",
                "",
                "This will be my final Kraken Friday. It was fun while it lasted.",
                "",
                "Soap kill.",
                "",
                "Splash kill.",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert "soap" in result
    # Should extract the explicit Lather: line, not the ambiguous "Soap kill." line
    assert result["soap"]["original"] == "Mickey Lee Soapworks - The Kraken - Soap"
    # Normalization strips trailing "Soap" product type indicator
    assert result["soap"]["normalized"] == "Mickey Lee Soapworks - The Kraken"


def test_parse_comment_soap_explicit_soap_wins_over_ambiguous_lather():
    """Test that explicit 'Soap:' pattern wins over ambiguous 'Lather' pattern."""
    comment = {
        "body": "\n".join(
            [
                "* **Brush:** Omega",
                "* **Razor:** Game Changer",
                "* **Blade:** Feather",
                "* **Soap:** Some Soap Co. - Test Soap",
                "",
                "Lather was great today, really enjoyed it.",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert "soap" in result
    # Should extract the explicit Soap: line, not the ambiguous "Lather was great" line
    assert result["soap"]["original"] == "Some Soap Co. - Test Soap"
    assert result["soap"]["normalized"] == "Some Soap Co. - Test Soap"


def test_parse_comment_soap_multiple_explicit_same_priority():
    """Test that when multiple explicit patterns match, first match wins."""
    comment = {
        "body": "\n".join(
            [
                "* **Brush:** Omega",
                "* **Razor:** Game Changer",
                "* **Blade:** Feather",
                "* **Soap:** Soap A",
                "* **Lather:** Soap B",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert "soap" in result
    # Should extract whichever appears first in the comment (first match wins within same priority)
    assert result["soap"]["original"] == "Soap A"
    assert result["soap"]["normalized"] == "Soap A"


def test_parse_comment_soap_list_item_preferred_over_narrative():
    """Test that list items (with * prefix) are preferred over narrative text at same priority."""
    # This tests the case where both "* **Lather:** ..." and "**Soap:** ..." match pattern 0,
    # but the list item should win even though "soap" comes before "lather" in alias order
    comment = {
        "body": "\n".join(
            [
                "* **Brush:** Wilkinson Sword Classic",
                "* **Razor:** Wilkinson Sword Classic $PLASTIC",
                "* **Blade:** Treet Silver (3)",
                "* **Lather:** Palmolive - Classic - Cream",
                "* **Post Shave:** Thayer's - Witch Hazel Toner - Aftershave",
                "",
                "Some narrative text here.",
                "",
                "**Soap:** Purchased at the outrageous price of 3 Canadian dollars ($2.20usd) for a 100ml tube from a pharmacy near my parents; considering this usually sells for under 2€ I guess it's a small premium to find it locally.",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert "soap" in result
    # Should extract the list item "* **Lather:** ..." not the narrative "**Soap:** ..."
    assert result["soap"]["original"] == "Palmolive - Classic - Cream"
    # Normalization strips " - Cream" as a soap suffix (correct behavior)
    assert result["soap"]["normalized"] == "Palmolive - Classic"


def test_parse_comment_multi_field_same_line():
    """Test parsing comment with multiple fields on the same line (user's specific case)."""
    # This is the actual case from data/extracted/2025-07.json line 19820-19833
    comment = {
        "id": "n3m6xst",
        "body": (
            "* **Brush:** Stirling/Zenith - 510SE XL 31mm Boar.* **Razor:** Henson - AL 13 Mild.* "
            "**Blade:** Wizamet - Super Iridium.* **Lather:** Stirling Soap Co. - r/wetshaving l, Rich Moose soap.* "
            "**Post Shave:** Stirling Soap Co. - Satsuma splash.* **Post Shave:** Stirling Soap Co. - Satsuma balm."
        ),
        "created_utc": "2025-07-17T12:02:56Z",
        "thread_id": "1m1zs53",
        "thread_title": "Thursday SOTD Thread - Jul 17, 2025",
        "url": "https://www.reddit.com/r/Wetshaving/comments/1m1zs53/thursday_sotd_thread_jul_17_2025/n3m6xst/",
    }

    result = parse_comment(comment)
    assert result is not None

    # Verify all fields extract correctly
    # Note: The period before the field separator is not included in the field value
    assert "brush" in result
    assert result["brush"]["original"] == "Stirling/Zenith - 510SE XL 31mm Boar"
    assert result["brush"]["normalized"] == "Stirling/Zenith - 510SE XL 31mm Boar"

    assert "razor" in result
    assert result["razor"]["original"] == "Henson - AL 13 Mild"
    assert result["razor"]["normalized"] == "Henson - AL 13 Mild"

    assert "blade" in result
    assert result["blade"]["original"] == "Wizamet - Super Iridium"
    assert result["blade"]["normalized"] == "Wizamet - Super Iridium"

    assert "soap" in result
    # Note: "Post Shave" is not a recognized field, so extraction continues to end of line
    # This is expected behavior - we only stop at recognized field markers
    assert result["soap"]["original"] == (
        "Stirling Soap Co. - r/wetshaving l, Rich Moose soap.* **Post Shave:** "
        "Stirling Soap Co. - Satsuma splash.* **Post Shave:** Stirling Soap Co. - Satsuma balm."
    )
    assert result["soap"]["normalized"] == (
        "Stirling Soap Co. - r/wetshaving l, Rich Moose soap. Post Shave: "
        "Stirling Soap Co. - Satsuma splash. Post Shave: Stirling Soap Co. - Satsuma balm"
    )


def test_parse_comment_multiple_lather_entries_line_order():
    """Test that earlier Lather entry is preferred over later Spotlight On entry."""
    comment = {
        "body": "\n".join(
            [
                "**Lather**: B&M Eigengrau Excelsior",
                "",
                "**Spotlight On:**",
                "",
                "**Lather:** B&M has a dark Gothic Teutonic side. This can be seen very clearly in Eigengrau. The chilly iris note blends well with the fir notes from First Snow, and the overall tone is somber, reserved, and Arctic. Only thing lacking here is menthol, but that addition may have messed the fine olfactory poise seen here up.",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert "soap" in result
    assert result["soap"]["original"] == "B&M Eigengrau Excelsior"
    assert result["soap"]["normalized"] == "B&M Eigengrau Excelsior"


def test_parse_comment_low_priority_fallback():
    """Test that low-priority patterns are tried if high-priority finds nothing."""
    comment = {
        "body": "\n".join(
            [
                "Some narrative text",
                "Soap B&M Eigengrau",  # Ambiguous pattern (no colon/dash)
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert "soap" in result
    assert result["soap"]["original"] == "B&M Eigengrau"


def test_parse_comment_line_order_high_priority():
    """Test that line order matters for high-priority patterns."""
    comment = {
        "body": "\n".join(
            [
                "**Soap:** First Soap",
                "**Soap:** Second Soap",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert "soap" in result
    assert result["soap"]["original"] == "First Soap"


def test_parse_comment_joins_wrapped_brush_after_trailing_dash():
    """Join a wrapped brush model when the field line ends with Brand -."""
    comment = {
        "body": "\n".join(
            [
                "* **Brush:** Chisel and Hound -",
                '"DinoS\'mores" w/26 mm v27 Fanchurian',
                "* **Razor:** GEM - Micromatic Open Comb",
                "* **Blade:** Accutec Pro - GEM (22nd use)",
                "* **Lather:** House of Mammoth - Hygge",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert result["brush"]["original"] == 'Chisel and Hound - "DinoS\'mores" w/26 mm v27 Fanchurian'
    assert result["razor"]["original"] == "GEM - Micromatic Open Comb"


def test_parse_comment_joins_unquoted_wrapped_brush_continuation():
    """Join an unquoted wrapped brush continuation after a trailing dash."""
    comment = {
        "body": "\n".join(
            [
                "* **Brush:** AP Shave Co. x Shavemac -",
                "Crushed Mud w/ 25 mm Mühle STF",
                "* **Razor:** Oliworks - M3terorite Aluminum",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert result["brush"]["original"] == "AP Shave Co. x Shavemac - Crushed Mud w/ 25 mm Mühle STF"
    assert result["razor"]["original"] == "Oliworks - M3terorite Aluminum"


def test_parse_comment_does_not_join_trailing_dash_when_next_line_is_field():
    """Keep a stylistic trailing dash when the next line is another field."""
    comment = {
        "body": "\n".join(
            [
                "* **Lather:** Bartigan & Stark - Campione -",
                "* **Post Shave:** Thayers - Unscented Facial Toner",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert result["soap"]["original"] == "Bartigan & Stark - Campione -"


def test_parse_comment_does_not_join_trailing_dash_across_blank_line():
    """Do not treat narrative after a blank line as a wrapped field continuation."""
    comment = {
        "body": "\n".join(
            [
                "* **Lather:** Stirling - Christmas Eve -",
                "",
                "Great shave today",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert result["soap"]["original"] == "Stirling - Christmas Eve -"


def test_parse_comment_prefilter_alias_as_substring():
    """A line containing an alias only inside a longer word extracts nothing.

    Guards the alias prefilter: "razorback" contains "razor" as a
    substring, so the line is admitted, but the \\brazor\\b pattern must
    still not match.
    """
    comment = {"body": "My razorback knife is sharp.\n* **Soap:** Tabac"}
    result = parse_comment(comment)
    assert result is not None
    assert "razor" not in result
    assert result["soap"]["original"] == "Tabac"


def test_parse_comment_prefilter_combined_alias():
    """A combined soap alias ("Soap & A/S") still extracts via the prefilter."""
    comment = {"body": "* Soap & A/S: Tabac\n* **Razor:** Blackbird"}
    result = parse_comment(comment)
    assert result is not None
    assert result["soap"]["original"] == "Tabac"
    assert result["razor"]["original"] == "Blackbird"


def test_parse_comment_prefilter_skips_non_field_lines():
    """Many narrative lines without any alias do not disturb extraction."""
    comment = {
        "body": "\n".join(
            [
                "Great shave today, really enjoyed it.",
                "The lather was thick and slick.",
                "No nicks or irritation at all.",
                "Will definitely use this combo again.",
                "* **Razor:** Blackbird",
                "Finished with a cold water rinse.",
            ]
        )
    }
    result = parse_comment(comment)
    assert result is not None
    assert result["razor"]["original"] == "Blackbird"


def test_field_patterns_cached():
    """Per-field pattern lists are built once and reused across comments."""
    from sotd.extract.comment import _get_field_patterns

    assert _get_field_patterns("razor") is _get_field_patterns("razor")
    assert _get_field_patterns("soap") is _get_field_patterns("soap")
