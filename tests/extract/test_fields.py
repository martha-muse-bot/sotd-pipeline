from sotd.utils.text import preprocess_body
from sotd.extract.fields import extract_field


def test_extract_field_lines():
    cases = {
        "razor": [
            ("* **Razor:** Blackbird", "Blackbird"),
            ("* **Razor**: Blackbird", "Blackbird"),
            ("* **razor:** Karve CB", "Karve CB"),
            ("* Razor: Henson AL13", "Henson AL13"),
            ("Razor: Game Changer", "Game Changer"),
            ("* ##Razor## - Henson AL-13+", "Henson AL-13+"),
            ("* Razor - Henson Al13+", "Henson Al13+"),
            ("* Razor = Henson AL-13+", "Henson AL-13+"),
            ("Razor = Henson AL-13+", "Henson AL-13+"),
            ("* **Blade:** Astra", None),
            ("- **Razor:** Blackland Vector", "Blackland Vector"),
            ("* **Razor** : Pearl L-55", "Pearl L-55"),
            ("🪒 *Razor:* Dollar Tree Safety Razor", "Dollar Tree Safety Razor"),
            (preprocess_body("\\* \\*\\*Razor:\\*\\* Gillette Superspeed"), "Gillette Superspeed"),
            # Razor Test should be ignored (not treated as razor field)
            ("Razor Test - Received Edge with CrOx Stropping", None),
            ("Razor Test - 20 Laps on Green CrOx - 50 on Leather", None),
            ("razor test - some description", None),
            ("RAZOR TEST - Another test", None),
            # But normal razor should still work
            ("Razor: Game Changer", "Game Changer"),
            (
                'Razor: Portland Cutlery Steinmetz "Salamander"',
                'Portland Cutlery Steinmetz "Salamander"',
            ),
        ],
        "blade": [
            ("* **Blade:** Feather", "Feather"),
            ("* **Blade**: Feather", "Feather"),
            ("* **blade:** Astra SP", "Astra SP"),
            ("* Blade: Nacet(x2)", "Nacet(x2)"),
            ("Blade: GSB", "GSB"),
            ("* ##Blade## - VOLSHOD", "VOLSHOD"),
            ("* Blade - Shark Super Chrome", "Shark Super Chrome"),
            ("* Blade = Feather", "Feather"),
            ("Blade = Feather", "Feather"),
            ("* **Soap:** Tabac", None),
            ("- **Blade:** Schick Proline", "Schick Proline"),
            ("* **Blade** : Gillette Winner", "Gillette Winner"),
            ("🧴 *Blade:* Dollar Tree Safety Razor", "Dollar Tree Safety Razor"),
            # Blade Test should be ignored (not treated as blade field)
            ("Blade Test - Some test description", None),
            ("blade test - another test", None),
        ],
        "brush": [
            ("* **Brush:** Simpson T3", "Simpson T3"),
            ("* **Brush**: Simpson T3", "Simpson T3"),
            ("* **brush:** Omega Boar", "Omega Boar"),
            ("* Brush: Power Ranger brush", "Power Ranger brush"),
            ("Brush: Boti White Boar", "Boti White Boar"),
            ("* ##Brush## - Yaqi Sagrada Familia", "Yaqi Sagrada Familia"),
            ("* Brush - Rocky Mountain - Badger", "Rocky Mountain - Badger"),
            ("* Brush = Omega synthetic", "Omega synthetic"),
            ("Brush = Omega synthetic", "Omega synthetic"),
            ("* **Blade:** Nacet", None),
            ("- **Brush:** C&H Odin's Beard", "C&H Odin's Beard"),
            ("* **Brush** : Zenith Boar", "Zenith Boar"),
            # Brush Test should be ignored (not treated as brush field)
            ("Brush Test - Some test description", None),
            ("brush test - another test", None),
        ],
        "soap": [
            ("* **Soap:** B&M Seville", "B&M Seville"),
            ("* **Soap**: B&M Seville", "B&M Seville"),
            ("* **soap:** Stirling Bay Rum", "Stirling Bay Rum"),
            ("* Soap: Tabac", "Tabac"),
            ("Soap: Cella Red", "Cella Red"),
            ("* ##Lather## - CBL Inconceivable", "CBL Inconceivable"),
            ("* **Razor:** Game Changer", None),
            ("- **Soap:** MWF", "MWF"),
            ("* **Soap** : Arko", "Arko"),
            ("* Soap - Arko Stick", "Arko Stick"),
            ("* Lather = DR Harris Lavender", "DR Harris Lavender"),
            ("Lather = DR Harris Lavender", "DR Harris Lavender"),
            ("* Soap = DR Harris Lavender", "DR Harris Lavender"),
            ("Soap = DR Harris Lavender", "DR Harris Lavender"),
            # Lather variations
            ("* **Lather:** B&M Seville", "B&M Seville"),
            ("* **Lather**: B&M Seville", "B&M Seville"),
            ("* **lather:** Stirling Bay Rum", "Stirling Bay Rum"),
            ("* Lather: Tabac", "Tabac"),
            ("Lather: Cella Red", "Cella Red"),
            (
                "* ##Soap## - CBL Inconceivable",
                "CBL Inconceivable",
            ),  # Already covered Lather, making sure Soap also works with this
            ("- **Lather:** MWF", "MWF"),
            ("* **Lather** : Arko", "Arko"),
            ("* Lather - Arko Stick", "Arko Stick"),
            # Additional patterns from get_patterns for both Soap and Lather
            ("* **Soap:** Some Soap Co.", "Some Soap Co."),  # Basic with colon
            (
                "* **Lather**: Another Lather Co.",
                "Another Lather Co.",
            ),  # Basic with space after colon
            ("Soap: Yet Another Soap", "Yet Another Soap"),  # No markdown, simple case
            ("Lather: Yet Another Lather", "Yet Another Lather"),  # No markdown, simple case
            ("* ##Soap## - Special Soap", "Special Soap"),  # Double hash
            ("* ##Lather## - Special Lather", "Special Lather"),  # Double hash
            ("- **Soap:** Hyphen Soap", "Hyphen Soap"),  # Hyphen prefix
            ("- **Lather:** Hyphen Lather", "Hyphen Lather"),  # Hyphen prefix
            ("🧴 *Soap:* Emoji Soap", "Emoji Soap"),  # Emoji prefix
            ("🧴 *Lather:* Emoji Lather", "Emoji Lather"),  # Emoji prefix
            (
                preprocess_body("\\* \\*\\*Soap:\\*\\* Escaped Soap"),
                "Escaped Soap",
            ),  # Preprocessed/escaped
            (
                preprocess_body("\\* \\*\\*Lather:\\*\\* Escaped Lather"),
                "Escaped Lather",
            ),  # Preprocessed/escaped
            ("* __Soap:__ Underlined Soap", "Underlined Soap"),  # Underscore emphasis
            ("* __Lather:__ Underlined Lather", "Underlined Lather"),  # Underscore emphasis
            ("* **Soap //** Forward Slash Soap", "Forward Slash Soap"),  # Forward slash separation
            (
                "* **Lather //** Forward Slash Lather",
                "Forward Slash Lather",
            ),  # Forward slash separation
            ("‣ **Soap**: Bullet Soap", "Bullet Soap"),  # Different bullet
            ("‣ **Lather**: Bullet Lather", "Bullet Lather"),  # Different bullet
            ("* **Soap** - Dash Separated Soap", "Dash Separated Soap"),  # Dash separated
            ("* **Lather** - Dash Separated Lather", "Dash Separated Lather"),  # Dash separated
            # Lather Games should be ignored (not treated as soap field)
            ("Lather Games Day 1 - Spring into Lather Games", None),
            ("* **Lather Games** - Some Event", None),
            ("Lather games are fun", None),
            ("LATHER GAMES EVENT", None),
            # But normal lather should still work
            ("* **Lather:** B&M Seville", "B&M Seville"),
            ("Lather: Tabac", "Tabac"),
        ],
    }

    for field, tests in cases.items():
        for line, expected in tests:
            assert extract_field(line, field) == expected


def test_extract_field_multi_field_same_line():
    """Test extraction when multiple fields appear on the same line."""
    # User's specific case: all fields on one line separated by .* **Field:
    multi_field_line = (
        "* **Brush:** Stirling/Zenith - 510SE XL 31mm Boar.* **Razor:** Henson - AL 13 Mild.* "
        "**Blade:** Wizamet - Super Iridium.* **Lather:** Stirling Soap Co. - r/wetshaving l, Rich Moose soap."
    )

    assert extract_field(multi_field_line, "brush") == "Stirling/Zenith - 510SE XL 31mm Boar"
    assert extract_field(multi_field_line, "razor") == "Henson - AL 13 Mild"
    assert extract_field(multi_field_line, "blade") == "Wizamet - Super Iridium"
    assert (
        extract_field(multi_field_line, "soap")
        == "Stirling Soap Co. - r/wetshaving l, Rich Moose soap."
    )

    # Test other field combinations
    razor_blade_line = "* **Razor:** Game Changer.* **Blade:** Feather"
    assert extract_field(razor_blade_line, "razor") == "Game Changer"
    assert extract_field(razor_blade_line, "blade") == "Feather"

    brush_soap_line = "* **Brush:** Omega.* **Soap:** Tabac"
    assert extract_field(brush_soap_line, "brush") == "Omega"
    assert extract_field(brush_soap_line, "soap") == "Tabac"

    # Test backward compatibility: single field per line still works
    single_field_line = "* **Razor:** Blackbird"
    assert extract_field(single_field_line, "razor") == "Blackbird"

    # Test field at end of line (no next field marker)
    end_of_line = "* **Brush:** Simpson T3"
    assert extract_field(end_of_line, "brush") == "Simpson T3"

    # Test with different separator formats
    simple_separator = "Razor: Game Changer.* Blade: Feather"
    assert extract_field(simple_separator, "razor") == "Game Changer"
    assert extract_field(simple_separator, "blade") == "Feather"

    # Test separator without period (just * between fields)
    no_period_separator = "* **Brush:** Yaqi - Moka Express 2 Band Badger* **Razor:** Henson - AL 13 Mild* **Blade:** Personna Platinum"
    assert extract_field(no_period_separator, "brush") == "Yaqi - Moka Express 2 Band Badger"
    assert extract_field(no_period_separator, "razor") == "Henson - AL 13 Mild"
    assert extract_field(no_period_separator, "blade") == "Personna Platinum"


def test_extract_field_equals_delimiter_priority():
    """Test that equals sign delimiter has lower priority than colon and dash."""
    # Colon should match before equals
    assert extract_field("* Razor: Henson AL-13+", "razor") == "Henson AL-13+"
    assert extract_field("* Razor = Henson AL-13+", "razor") == "Henson AL-13+"

    # Dash should match before equals
    assert extract_field("* Razor - Henson AL-13+", "razor") == "Henson AL-13+"
    assert extract_field("* Razor = Henson AL-13+", "razor") == "Henson AL-13+"

    # Equals should work when colon/dash not present
    assert extract_field("* Brush = Omega synthetic", "brush") == "Omega synthetic"
    assert extract_field("Brush = Omega synthetic", "brush") == "Omega synthetic"

    # Test that equals delimiter extracts value correctly (not including the =)
    assert extract_field("* Lather = DR Harris Lavender", "soap") == "DR Harris Lavender"
    assert extract_field("Lather = DR Harris Lavender", "soap") == "DR Harris Lavender"


def test_get_compiled_patterns_match_get_patterns():
    """Compiled cache returns the same patterns as get_patterns(), cached."""
    from sotd.extract.fields import get_compiled_patterns, get_patterns
    from sotd.utils.aliases import FIELD_ALIASES

    for aliases in FIELD_ALIASES.values():
        for alias in aliases:
            compiled = get_compiled_patterns(alias)
            strings = get_patterns(alias)
            assert len(compiled) == len(strings)
            assert [p.pattern for p in compiled] == strings
            # Same list object on repeat call: built once per alias.
            assert get_compiled_patterns(alias) is compiled


def test_extract_field_with_pattern_accepts_compiled_pattern():
    """String and compiled forms of a pattern extract identically."""
    import re

    from sotd.extract.fields import extract_field_with_pattern, get_compiled_patterns

    line = "* **Razor:** Blackbird"
    pattern = get_compiled_patterns("razor")[0]
    assert isinstance(pattern, re.Pattern)
    assert extract_field_with_pattern(line, "razor", pattern) == "Blackbird"
    assert extract_field_with_pattern(line, "razor", pattern.pattern) == "Blackbird"
    assert extract_field_with_pattern("* **Soap:** Tabac", "razor", pattern) is None
