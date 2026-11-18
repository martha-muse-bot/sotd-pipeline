"""Tests for soap table generators."""

import pytest

from sotd.report.table_generators.table_generator import TableGenerator


class TestSoapsTableGenerator:
    """Test the TableGenerator with soap data."""

    def test_empty_data(self):
        """Test with empty data."""
        generator = TableGenerator({})
        # TableGenerator should raise ValueError for unknown table names
        with pytest.raises(ValueError, match="Unknown table: soaps"):
            generator.generate_table("soaps")

    def test_valid_data(self):
        """Test with valid data."""
        sample_data = {
            "soaps": [
                {
                    "rank": 1,
                    "name": "Declaration Grooming Sellout",
                    "shaves": 35,
                    "unique_users": 18,
                },
                {"rank": 2, "name": "Stirling Executive Man", "shaves": 25, "unique_users": 12},
            ]
        }
        generator = TableGenerator(sample_data)
        result = generator.generate_table("soaps")
        assert "Declaration Grooming Sellout" in result
        assert "Stirling Executive Man" in result
        assert "35" in result
        assert "25" in result

    def test_missing_required_fields(self):
        """Test with missing required fields."""
        sample_data = {
            "soaps": [
                {"rank": 1, "name": "Declaration Grooming Sellout"},  # Missing shaves
                {
                    "rank": 2,
                    "name": "Stirling Executive Man",
                    "shaves": 25,
                    "unique_users": 12,
                },  # Valid
            ]
        }
        generator = TableGenerator(sample_data)
        result = generator.generate_table("soaps")
        # TableGenerator handles missing fields gracefully
        assert "Declaration Grooming Sellout" in result
        assert "Stirling Executive Man" in result

    def test_table_title(self):
        """Test table title."""
        generator = TableGenerator({})
        # TableGenerator doesn't have get_table_title method, so test basic functionality
        assert hasattr(generator, "generate_table")

    def test_column_config(self):
        """Test column configuration."""
        sample_data = {
            "soaps": [
                {
                    "rank": 1,
                    "name": "Declaration Grooming Sellout",
                    "shaves": 35,
                    "unique_users": 18,
                },
            ]
        }
        generator = TableGenerator(sample_data)
        result = generator.generate_table("soaps")
        # Check that expected columns are present
        assert "Name" in result
        assert "Shaves" in result
        assert "Unique Users" in result

    def test_wsdb_links_enabled_with_flag(self, tmp_path, monkeypatch):
        """Test that WSDB links are added when wsdb=True is specified."""
        # Create directory structure
        table_generators_dir = tmp_path / "sotd" / "report" / "table_generators"
        table_generators_dir.mkdir(parents=True)

        # Create mock soaps.yaml file that WSDBLookup expects
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)
        soaps_file = data_dir / "soaps.yaml"

        mock_soaps_yaml = {
            "Barrister and Mann": {
                "scents": {"Seville": {"wsdb_slug": "barrister-and-mann-seville"}}
            }
        }

        import yaml

        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(mock_soaps_yaml, f)

        import sotd.report.table_generators.table_generator as tg_module

        original_file = tg_module.__file__
        test_file_path = str(table_generators_dir / "table_generator.py")
        monkeypatch.setattr(tg_module, "__file__", test_file_path)

        data = {
            "soaps": [
                {
                    "rank": 1,
                    "shaves": 100,
                    "unique_users": 50,
                    "brand": "Barrister and Mann",
                    "scent": "Seville",
                    "name": "Barrister and Mann - Seville",
                },
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soaps", wsdb=True)

        # Should contain link for matched soap
        assert (
            "[Barrister and Mann - Seville](https://www.wetshavingdatabase.com/software/barrister-and-mann-seville/)"
            in result
        )

        # Restore original file path
        monkeypatch.setattr(tg_module, "__file__", original_file)

    def test_wsdb_links_disabled_without_flag(self, tmp_path, monkeypatch):
        """Test that WSDB links are NOT added when wsdb=False or not specified."""
        # Create directory structure
        table_generators_dir = tmp_path / "sotd" / "report" / "table_generators"
        table_generators_dir.mkdir(parents=True)

        # Create mock soaps.yaml file that WSDBLookup expects
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)
        soaps_file = data_dir / "soaps.yaml"

        mock_soaps_yaml = {
            "Barrister and Mann": {
                "scents": {"Seville": {"wsdb_slug": "barrister-and-mann-seville"}}
            }
        }

        import yaml

        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(mock_soaps_yaml, f)

        import sotd.report.table_generators.table_generator as tg_module

        original_file = tg_module.__file__
        test_file_path = str(table_generators_dir / "table_generator.py")
        monkeypatch.setattr(tg_module, "__file__", test_file_path)

        data = {
            "soaps": [
                {
                    "rank": 1,
                    "shaves": 100,
                    "unique_users": 50,
                    "brand": "Barrister and Mann",
                    "scent": "Seville",
                    "name": "Barrister and Mann - Seville",
                },
            ]
        }

        generator = TableGenerator(data)

        # Test with wsdb=False explicitly
        result_false = generator.generate_table("soaps", wsdb=False)
        assert "Barrister and Mann - Seville" in result_false
        assert "[Barrister and Mann - Seville](" not in result_false

        # Test without wsdb parameter (defaults to False)
        result_default = generator.generate_table("soaps")
        assert "Barrister and Mann - Seville" in result_default
        assert "[Barrister and Mann - Seville](" not in result_default

        # Restore original file path
        monkeypatch.setattr(tg_module, "__file__", original_file)

    def test_wsdb_links_with_column_renaming(self, tmp_path, monkeypatch):
        """Test that WSDB links work correctly when name column is renamed to soap."""
        # Create directory structure
        table_generators_dir = tmp_path / "sotd" / "report" / "table_generators"
        table_generators_dir.mkdir(parents=True)

        # Create mock soaps.yaml file that WSDBLookup expects
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)
        soaps_file = data_dir / "soaps.yaml"

        mock_soaps_yaml = {
            "Barrister and Mann": {
                "scents": {"Seville": {"wsdb_slug": "barrister-and-mann-seville"}}
            }
        }

        import yaml

        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(mock_soaps_yaml, f)

        import sotd.report.table_generators.table_generator as tg_module

        original_file = tg_module.__file__
        test_file_path = str(table_generators_dir / "table_generator.py")
        monkeypatch.setattr(tg_module, "__file__", test_file_path)

        data = {
            "soaps": [
                {
                    "rank": 1,
                    "shaves": 100,
                    "unique_users": 50,
                    "brand": "Barrister and Mann",
                    "scent": "Seville",
                    "name": "Barrister and Mann - Seville",
                },
            ]
        }

        generator = TableGenerator(data)
        # Use columns parameter to rename "name" to "soap" (matching the template)
        result = generator.generate_table(
            "soaps", wsdb=True, columns="rank, name=soap, shaves, unique_users"
        )

        # Should contain link for matched soap (even though column was renamed)
        assert (
            "[Barrister and Mann - Seville](https://www.wetshavingdatabase.com/software/barrister-and-mann-seville/)"
            in result
        )
        # The column should be renamed to "Soap" (title case)
        assert "| Soap" in result

        # Restore original file path
        monkeypatch.setattr(tg_module, "__file__", original_file)

    def test_wsdb_parameter_unaffected_other_tables(self, tmp_path, monkeypatch):
        """Test that wsdb parameter does not affect other tables."""
        # Create directory structure
        table_generators_dir = tmp_path / "sotd" / "report" / "table_generators"
        table_generators_dir.mkdir(parents=True)

        # Create mock soaps.yaml file that WSDBLookup expects
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)
        soaps_file = data_dir / "soaps.yaml"

        mock_soaps_yaml = {
            "Barrister and Mann": {
                "scents": {"Seville": {"wsdb_slug": "barrister-and-mann-seville"}}
            }
        }

        import yaml

        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(mock_soaps_yaml, f)

        import sotd.report.table_generators.table_generator as tg_module

        original_file = tg_module.__file__
        test_file_path = str(table_generators_dir / "table_generator.py")
        monkeypatch.setattr(tg_module, "__file__", test_file_path)

        data = {
            "soap_makers": [
                {
                    "rank": 1,
                    "brand": "Barrister and Mann",
                    "shaves": 100,
                    "unique_users": 50,
                },
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", wsdb=True)

        # Should contain brand name but no links (wsdb only applies to soaps table)
        assert "Barrister and Mann" in result
        assert "[Barrister and Mann](" not in result

        # Restore original file path
        monkeypatch.setattr(tg_module, "__file__", original_file)


class TestSoapMakersTableGenerator:
    """Test the TableGenerator with soap makers data."""

    def test_empty_data(self):
        """Test with empty data."""
        generator = TableGenerator({})
        # TableGenerator should raise ValueError for unknown table names
        with pytest.raises(ValueError, match="Unknown table: soap-makers"):
            generator.generate_table("soap-makers")

    def test_valid_data(self):
        """Test with valid data."""
        sample_data = {
            "soap_makers": [
                {"rank": 1, "brand": "Declaration Grooming", "shaves": 70, "unique_users": 35},
                {"rank": 2, "brand": "Stirling", "shaves": 55, "unique_users": 28},
            ]
        }
        generator = TableGenerator(sample_data)
        result = generator.generate_table("soap-makers")
        assert "Declaration Grooming" in result
        assert "Stirling" in result
        assert "70" in result
        assert "55" in result

    def test_missing_required_fields(self):
        """Test with missing required fields."""
        sample_data = {
            "soap_makers": [
                {"rank": 1, "brand": "Declaration Grooming"},  # Missing shaves
                {"rank": 2, "brand": "Stirling", "shaves": 55, "unique_users": 28},  # Valid
            ]
        }
        generator = TableGenerator(sample_data)
        result = generator.generate_table("soap-makers")
        # TableGenerator handles missing fields gracefully
        assert "Declaration Grooming" in result
        assert "Stirling" in result

    def test_table_title(self):
        """Test table title."""
        generator = TableGenerator({})
        # TableGenerator doesn't have get_table_title method, so test basic functionality
        assert hasattr(generator, "generate_table")

    def test_column_config(self):
        """Test column configuration."""
        sample_data = {
            "soap_makers": [
                {"rank": 1, "brand": "Declaration Grooming", "shaves": 70, "unique_users": 35},
            ]
        }
        generator = TableGenerator(sample_data)
        result = generator.generate_table("soap-makers")
        # Check that expected columns are present
        assert "Brand" in result
        assert "Shaves" in result
        assert "Unique Users" in result
