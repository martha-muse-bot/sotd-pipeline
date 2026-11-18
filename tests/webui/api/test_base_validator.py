import tempfile
from pathlib import Path

import yaml

# Import the base validator class (will be created)
from webui.api.validators.base_validator import BaseValidator


class TestBaseValidator:
    """Unit tests for the BaseValidator base class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_yaml_path = Path(self.temp_dir) / "test_data.yaml"

        # Create test data
        self.test_data = {
            "items": {
                "Test Item 1": {"field1": "value1", "field2": "value2", "validated": True},
                "Test Item 2": {"field1": "value3", "field2": "value4", "validated": False},
            }
        }

        # Write test data to file
        with open(self.test_yaml_path, "w") as f:
            yaml.dump(self.test_data, f)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_yaml_path.exists():
            self.test_yaml_path.unlink()
        if Path(self.temp_dir).exists():
            import shutil

            shutil.rmtree(self.temp_dir)

    def test_base_validator_initialization(self):
        """Test that BaseValidator initializes correctly."""
        validator = BaseValidator(self.test_yaml_path)

        assert validator.yaml_path == self.test_yaml_path
        assert validator.data == {}
        assert validator.is_loaded is False

    def test_load_data_success(self):
        """Test successful data loading."""
        validator = BaseValidator(self.test_yaml_path)
        result = validator.load_data()

        assert result.success is True
        assert result.data == self.test_data
        assert validator.is_loaded is True
        assert validator.data == self.test_data

    def test_load_data_file_not_found(self):
        """Test data loading when file doesn't exist."""
        non_existent_path = Path("/non/existent/file.yaml")
        validator = BaseValidator(non_existent_path)
        result = validator.load_data()

        assert result.success is False
        assert result.error_message is not None
        assert "File not found" in result.error_message
        assert validator.is_loaded is False

    def test_load_data_invalid_yaml(self):
        """Test data loading with invalid YAML."""
        # Create invalid YAML file
        invalid_yaml_path = Path(self.temp_dir) / "invalid.yaml"
        with open(invalid_yaml_path, "w") as f:
            f.write("invalid: yaml: content: [")

        validator = BaseValidator(invalid_yaml_path)
        result = validator.load_data()

        assert result.success is False
        assert result.error_message is not None
        assert "Invalid YAML" in result.error_message
        assert validator.is_loaded is False

    def test_save_data_success(self):
        """Test successful data saving."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        # Modify data
        new_data = {"items": {"New Item": {"field1": "new_value"}}}
        result = validator.save_data(new_data)

        assert result.success is True

        # Verify file was written
        with open(self.test_yaml_path, "r") as f:
            saved_data = yaml.safe_load(f)
        assert saved_data == new_data

    def test_save_data_directory_not_exists(self):
        """Test data saving when directory doesn't exist."""
        non_existent_dir = Path("/non/existent/dir") / "test.yaml"
        validator = BaseValidator(non_existent_dir)

        result = validator.save_data({"test": "data"})

        assert result.success is False
        # The error message varies by system, so check for any error
        assert result.error_message is not None
        assert len(result.error_message) > 0

    def test_validate_required_fields_success(self):
        """Test successful validation of required fields."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        required_fields = ["field1", "field2"]
        result = validator.validate_required_fields(required_fields)

        assert result.success is True
        assert result.validation_errors is not None
        assert len(result.validation_errors) == 0

    def test_validate_required_fields_missing(self):
        """Test validation when required fields are missing."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        required_fields = ["field1", "field2", "missing_field"]
        result = validator.validate_required_fields(required_fields)

        assert result.success is False
        assert result.validation_errors is not None
        assert len(result.validation_errors) > 0
        assert any("missing_field" in error for error in result.validation_errors)

    def test_validate_data_structure_success(self):
        """Test successful data structure validation."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        expected_structure = {"items": dict}
        result = validator.validate_data_structure(expected_structure)

        assert result.success is True
        assert result.validation_errors is not None
        assert len(result.validation_errors) == 0

    def test_validate_data_structure_invalid(self):
        """Test data structure validation with invalid structure."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        expected_structure = {"wrong_key": dict}
        result = validator.validate_data_structure(expected_structure)

        assert result.success is False
        assert result.validation_errors is not None
        assert len(result.validation_errors) > 0
        assert any("wrong_key" in error for error in result.validation_errors)

    def test_get_item_by_name_success(self):
        """Test successful item retrieval by name."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        item = validator.get_item_by_name("Test Item 1")

        assert item is not None
        assert item["field1"] == "value1"
        assert item["field2"] == "value2"

    def test_get_item_by_name_not_found(self):
        """Test item retrieval when item doesn't exist."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        item = validator.get_item_by_name("Non Existent Item")

        assert item is None

    def test_get_all_items(self):
        """Test retrieval of all items."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        items = validator.get_all_items()

        assert len(items) == 2
        assert "Test Item 1" in items
        assert "Test Item 2" in items

    def test_add_item_success(self):
        """Test successful item addition."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        new_item = {"field1": "new_value", "field2": "new_value2"}
        result = validator.add_item("New Item", new_item)

        assert result.success is True

        # Verify item was added
        added_item = validator.get_item_by_name("New Item")
        assert added_item == new_item

    def test_add_item_already_exists(self):
        """Test item addition when item already exists."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        new_item = {"field1": "new_value"}
        result = validator.add_item("Test Item 1", new_item)

        assert result.success is False
        assert result.error_message is not None
        assert "already exists" in result.error_message

    def test_update_item_success(self):
        """Test successful item update."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        updated_item = {"field1": "updated_value", "field2": "updated_value2"}
        result = validator.update_item("Test Item 1", updated_item)

        assert result.success is True

        # Verify item was updated
        updated = validator.get_item_by_name("Test Item 1")
        assert updated == updated_item

    def test_update_item_not_found(self):
        """Test item update when item doesn't exist."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        updated_item = {"field1": "updated_value"}
        result = validator.update_item("Non Existent Item", updated_item)

        assert result.success is False
        assert result.error_message is not None
        assert "not found" in result.error_message

    def test_delete_item_success(self):
        """Test successful item deletion."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        result = validator.delete_item("Test Item 1")

        assert result.success is True

        # Verify item was deleted
        deleted_item = validator.get_item_by_name("Test Item 1")
        assert deleted_item is None

    def test_delete_item_not_found(self):
        """Test item deletion when item doesn't exist."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        result = validator.delete_item("Non Existent Item")

        assert result.success is False
        assert result.error_message is not None
        assert "not found" in result.error_message

    def test_validate_item_data_success(self):
        """Test successful item data validation."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        item_data = {"field1": "value", "field2": "value2"}
        required_fields = ["field1", "field2"]
        result = validator.validate_item_data(item_data, required_fields)

        assert result.success is True
        assert result.validation_errors is not None
        assert len(result.validation_errors) == 0

    def test_validate_item_data_missing_fields(self):
        """Test item data validation with missing required fields."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        item_data = {"field1": "value"}  # Missing field2
        required_fields = ["field1", "field2"]
        result = validator.validate_item_data(item_data, required_fields)

        assert result.success is False
        assert result.validation_errors is not None
        assert len(result.validation_errors) > 0
        assert any("field2" in error for error in result.validation_errors)

    def test_backup_data_success(self):
        """Test successful data backup."""
        validator = BaseValidator(self.test_yaml_path)
        validator.load_data()

        backup_path = Path(self.temp_dir) / "backup.yaml"
        result = validator.backup_data(backup_path)

        assert result.success is True
        assert backup_path.exists()

        # Verify backup contains original data
        with open(backup_path, "r") as f:
            backup_data = yaml.safe_load(f)
        assert backup_data == self.test_data

    def test_backup_data_not_loaded(self):
        """Test backup when data is not loaded."""
        validator = BaseValidator(self.test_yaml_path)

        backup_path = Path(self.temp_dir) / "backup.yaml"
        result = validator.backup_data(backup_path)

        assert result.success is False
        assert result.error_message is not None
        assert "Data not loaded" in result.error_message

    def test_restore_data_success(self):
        """Test successful data restoration."""
        validator = BaseValidator(self.test_yaml_path)

        # Create backup file
        backup_path = Path(self.temp_dir) / "backup.yaml"
        with open(backup_path, "w") as f:
            yaml.dump(self.test_data, f)

        result = validator.restore_data(backup_path)

        assert result.success is True
        assert validator.data == self.test_data
        assert validator.is_loaded is True

    def test_restore_data_backup_not_found(self):
        """Test restoration when backup file doesn't exist."""
        validator = BaseValidator(self.test_yaml_path)

        non_existent_backup = Path("/non/existent/backup.yaml")
        result = validator.restore_data(non_existent_backup)

        assert result.success is False
        assert result.error_message is not None
        assert "Backup file not found" in result.error_message
