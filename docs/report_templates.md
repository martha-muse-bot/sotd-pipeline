# Report Templates

The SOTD Pipeline now supports flexible, customizable templates for both hardware and software reports through a unified architecture. This allows users to easily modify the entire report structure and content without changing the code.

## Overview

The template system uses Markdown files with variable replacement and table placeholders to generate complete reports. Templates are stored in `data/report_templates/` as individual `.md` files and can be easily edited by users to customize the entire report structure.

**New Architecture**: The system now uses a unified `MonthlyReportGenerator` class that handles both hardware and software reports, eliminating code duplication and providing a consistent interface for all monthly report generation.

**Consistent Variables and Tables**: Both monthly and annual reports share the same core variables and table placeholders, making template creation and maintenance much simpler. The system automatically provides the appropriate data based on the report type and time period.

## Template File Structure

The template system uses individual Markdown files in the `data/report_templates/` directory:

```
data/report_templates/
├── hardware.md              # Monthly hardware report template
├── software.md              # Monthly software report template
├── annual_hardware.md       # Annual hardware report template
└── annual_software.md       # Annual software report template
```

Each template file contains the complete report structure with variables and table placeholders. The system automatically loads templates based on the report type being generated.

**Note**: The monthly templates use the base names (`hardware.md`, `software.md`) rather than prefixed names, as the unified generator automatically selects the appropriate template based on the report type.

## Template Content Structure

Each template file contains the complete report content with variable placeholders and table placeholders. Here's an example structure:

```markdown
# Hardware Report - {{month_year}}

**Total Shaves:** {{total_shaves}}
**Unique Shavers:** {{unique_shavers}}

Welcome to your SOTD Hardware Report for {{month_year}}

## Notes & Caveats

* {{total_shaves}} shave reports from {{unique_shavers}} distinct shavers during the month of {{month_year}} were analyzed to produce this report.

## Razors

{{tables.razors}}

## Blades

{{tables.blades}}
```

**Note**: Each template file contains the complete report structure. The system automatically substitutes variables and table placeholders to generate the final report.

## Available Template Variables

### Shared Variables (Monthly and Annual Reports)

The following variables are available for both monthly and annual report templates:

| Variable | Description | Example Output |
|----------|-------------|----------------|
| `{{total_shaves}}` | Total number of shaves (formatted with commas) | `1,234` |
| `{{unique_shavers}}` | Number of unique users | `567` |
| `{{avg_shaves_per_user}}` | Average shaves per user | `2.2` |
| `{{median_shaves_per_user}}` | Median shaves per user | `1.0` |
| `{{total_samples}}` | Total number of sample/smush shaves used | `89` |
| `{{sample_percentage}}` | Percentage of shaves that used samples or smushes | `7.2%` |
| `{{sample_users}}` | Number of unique users who used samples or smushes | `67` |
| `{{sample_brands}}` | Number of unique brands sampled/smushed | `23` |

### Monthly Report Specific Variables

Additional variables available only for monthly reports:

| Variable | Description | Example Output |
|----------|-------------|----------------|
| `{{month_year}}` | Month and year in display format | `January 2025` |

### Hardware Report Specific Variables

Additional variables available for hardware reports (both monthly and annual):

| Variable | Description | Example Output |
|----------|-------------|----------------|
| `{{unique_razors}}` | Number of unique razors used | `234` |
| `{{unique_blades}}` | Number of unique blades used | `123` |
| `{{unique_brushes}}` | Number of unique brushes used | `89` |

### Software Report Specific Variables

Additional variables available for software reports (both monthly and annual):

| Variable | Description | Example Output |
|----------|-------------|----------------|
| `{{unique_soaps}}` | Number of unique soaps used | `585` |
| `{{unique_brands}}` | Number of unique soap brands/makers | `136` |

### Annual Report Specific Variables

Additional variables available only for annual reports:

| Variable | Description | Example Output |
|----------|-------------|----------------|
| `{{year}}` | Year in display format | `2025` |
| `{{included_months}}` | Number of months included in the data | `12` |
| `{{missing_months}}` | Number of months missing from the data | `0` |

## Available Table Placeholders

The following table placeholders are available for both monthly and annual reports:

### Hardware Report Tables

- `{{tables.razors}}` - Top razors by usage
- `{{tables.blades}}` - Top blades by usage  
- `{{tables.blade-usage-distribution}}` - Blade usage distribution (uses per blade)
- `{{tables.brushes}}` - Top brushes by usage
- `{{tables.soap-makers}}` - Top soap makers by usage
- `{{tables.soaps}}` - Top soaps by usage
- `{{tables.top-sampled-soaps}}` - Top sampled soaps by usage

### Software Report Tables

| Placeholder | Description | Content |
|-------------|-------------|---------|
| `{{tables.soap-makers}}` | Soap maker statistics | Top soap makers |
| `{{tables.soaps}}` | Soap usage statistics | Top soaps by usage |
| `{{tables.top-sampled-soaps}}` | Sample usage statistics | Top sampled soaps by usage |
| `{{tables.brand-diversity}}` | Brand diversity statistics | Unique scents per brand |
| `{{tables.top-shavers}}` | Top shaver statistics | Users with most shaves |

**Note**: The same table placeholders work identically in both monthly and annual reports. The system automatically generates the appropriate data based on the time period being reported.

## Enhanced Table Syntax

The template system now supports advanced table configuration through parameter-based syntax. This allows you to control table size, apply data filters, and manage tie handling without modifying the code.

### Basic Syntax

```markdown
{{tables.table_name|parameter:value|parameter:value}}
```

### Available Parameters

#### **Data Field Limits (Bottom Cutoffs)**
These parameters limit tables to items above numerical thresholds, respecting the existing table sorting:

```markdown
|shaves:N                # Must have >= N shaves (primary sort for most tables)
|unique_users:N          # Must have >= N unique users (secondary sort for most tables)
|missed_days:N           # Must have <= N missed days (secondary sort for users table)
|uses:N                  # Must have >= N uses (primary sort for highest use count table)
|unique_blades:N         # Must have >= N unique blades (primary sort for blade diversity)
|unique_brushes:N        # Must have >= N unique brushes (primary sort for brush diversity)
|unique_soaps:N          # Must have >= N unique soaps (primary sort for soap diversity)
|unique_combinations:N   # Must have >= N unique combinations (primary sort for soap brand scent diversity)
|unique_razors:N         # Must have >= N unique razors (primary sort for razor diversity)
|total_shaves:N          # Must have >= N total shaves (secondary sort for diversity tables)
|format:N                # Must have >= N format (primary sort for razor format users)
|fiber:N                 # Must have >= N fiber (primary sort for brush fiber users)
```

**Important**: Only columns involved in table sorting are available for limits. This ensures limits work as bottom cutoffs that respect the existing table order.

#### **Table Size Limits**
```markdown
|rows:N                  # Maximum N rows
|ranks:N                 # Maximum N ranks
```

### How Limits Work

#### **Bottom Cutoff Behavior**
- Limits are applied **after** the table is sorted
- Only items **above** the threshold are included
- This works naturally with existing table sorting (e.g., `shaves:5` for tables sorted by shaves descending)

#### **Tie Handling**
- **Ties are never broken** - complete ties are always included
- If including a tie would exceed row/rank limits, the table stops **before** the tie
- This ensures data integrity while respecting size constraints

#### **Processing Order**
1. **Apply data field limits** - Remove items below thresholds
2. **Apply size limits** - Respect row/rank constraints
3. **Handle ties** - Include complete ties when possible

### Template Examples

#### **Basic Usage**
```markdown
## Top 20 razors with 5+ shaves
{{tables.razors|shaves:5|rows:20}}

## Top 15 ranks, only popular items
{{tables.razors|unique_users:3|ranks:15}}

## Top 25 blades with 3+ shaves
{{tables.blades|shaves:3|rows:25}}
```

#### **Advanced Usage**
```markdown
## Top razors with 5+ shaves, max 20 rows
{{tables.razors|shaves:5|rows:20}}

## Top 15 ranks, only popular items
{{tables.razors|unique_users:3|ranks:15}}

## Top shavers (only active participants)
{{tables.top-shavers|shaves:20|missed_days:2|rows:10}}

## Only popular brush fibers
{{tables.brush-fibers|shaves:10|rows:25}}
```

### Available Limits by Table Type

#### **Standard Product Tables (Razors, Blades, Brushes, Soaps)**
- **Primary sort:** `shaves` (descending) → `|shaves:N`
- **Secondary sort:** `unique_users` (descending) → `|unique_users:N`

#### **User Tables (Top Shavers)**
- **Primary sort:** `shaves` (descending) → `|shaves:N`
- **Secondary sort:** `missed_days` (ascending) → `|missed_days:N`

#### **Diversity Tables**
- **Primary sort:** `unique_brushes`, `unique_blades`, `unique_soaps` (descending) → `|unique_brushes:N`, `|unique_blades:N`, `|unique_soaps:N`
- **Secondary sort:** `total_shaves` (descending) → `|total_shaves:N`

#### **Specialized User Tables**
- **Primary sort:** `format` or `fiber` (ascending) → `|format:N`, `|fiber:N`
- **Secondary sort:** `shaves` (descending) → `|shaves:N`

#### **Cross-Product Tables**
- **Primary sort:** `uses` (descending) → `|uses:N`

### Best Practices

1. **Use limits for quality control** - `|shaves:5` ensures only meaningful data is shown
2. **Control table size** - `|rows:20` prevents tables from becoming too long
3. **Respect sorting** - limits work with existing table order, not against it
4. **Combine limits thoughtfully** - `|shaves:5|rows:20` gives you quality + size control
5. **Test your limits** - verify that limits produce the expected results

### Error Handling

- **Invalid column names** will throw clear error messages
- **Non-sorting columns** cannot be used for limits (prevents confusion)
- **Invalid parameter values** will fall back to defaults
- **Conflicting parameters** will use priority order (data limits > size limits)

## How to Customize Templates

1. **Edit the template files**: Open the appropriate template file in `data/report_templates/` in your preferred text editor
2. **Modify content**: Change the text content as needed while preserving the Markdown structure
3. **Use variables**: Include variables where you want dynamic content (e.g., `{{total_shaves}}`)
4. **Add table placeholders**: Insert table placeholders where you want tables (e.g., `{{tables.razors}}`)
5. **Customize structure**: Organize sections, headers, and tables however you prefer
6. **Save changes**: The changes will take effect immediately on the next report generation

**Note**: With the unified architecture, you can now modify both hardware and software templates independently while maintaining consistent variable naming and structure.

## Template Syntax

### Variable Replacement

Variables use double curly braces: `{{variable_name}}`

Example:
```markdown
# Hardware Report - {{month_year}}
- **{{total_shaves}} shaves** were analyzed this month
```

### Table Placeholders

Table placeholders use the format: `{{tables.table-name}}`

Example:
```markdown
## Razor Statistics
{{tables.razors}}
{{tables.razor-manufacturers}}
```

### Markdown Formatting

Templates use standard Markdown syntax:
```markdown
# Main Header
## Section Header
### Subsection Header

* Bullet points
* More bullet points

**Bold text** and *italic text*

[Link text](URL)
```

## Customization Examples

### Minimal Hardware Template
```markdown
# Hardware Report - {{month_year}}

**Total Shaves:** {{total_shaves}}
**Unique Shavers:** {{unique_shavers}}

## Razors
{{tables.razors}}

## Blades
{{tables.blades}}

## Brushes
{{tables.brushes}}
```

### Detailed Hardware Template with Custom Headers
```markdown
# Hardware Report - {{month_year}}

**Total Shaves:** {{total_shaves}}
**Unique Shavers:** {{unique_shavers}}

## Notes & Caveats

This report covers hardware usage for {{total_shaves}} shaves from {{unique_shavers}} users.

## Razor Analysis

### Most Popular Razors
{{tables.razors}}

### Razor Manufacturers
{{tables.razor-manufacturers}}

## Blade Analysis

### Most Popular Blades
{{tables.blades}}

## Brush Analysis

### Most Popular Brushes
{{tables.brushes}}

### Handle Makers
{{tables.brush-handle-makers}}

### Knot Makers
{{tables.brush-knot-makers}}
```

### Software Template Example
```markdown
# Software Report - {{month_year}}

**Total Shaves:** {{total_shaves}}
**Unique Shavers:** {{unique_shavers}}

* {{total_shaves}} shave reports from {{unique_shavers}} distinct shavers during the month of {{month_year}} were analyzed to produce this report. Collectively, these shavers used {{unique_soaps}} distinct soaps from {{unique_brands}} distinct brands.

## Soap Makers
{{tables.soap-makers}}

## Soaps
{{tables.soaps}}

## Brand Diversity
{{tables.brand-diversity}}
```

## Testing Templates

The template system includes comprehensive testing to ensure templates work correctly:

### Test Fixtures
- Templates are stored in `tests/fixtures/report_template.yaml` for testing
- Tests use shared fixtures to avoid code duplication
- Both unit and integration tests use the same template structure

### Test Coverage
- **Unit tests**: Test template variable replacement and content generation
- **Integration tests**: Test complete report generation with sample data
- **Template validation**: Ensure templates load correctly and contain required sections
- **Unified generator tests**: Test the consolidated `MonthlyReportGenerator` class

### Running Template Tests
```bash
# Run all report tests
python -m pytest tests/report/ -v

# Run specific template tests
python -m pytest tests/report/test_template_integration.py -v

# Run monthly generator tests
python -m pytest tests/report/test_monthly_generator.py -v
```

## Error Handling

The system follows a **fast-fail** approach. If the template directory is missing, contains errors, or has missing template files, report generation will fail immediately with a clear error message. This ensures that configuration issues are caught early and explicitly.

**Common errors:**
- `Templates directory not found: data/report_templates` - Template directory is missing
- `Template 'hardware' not found. Available templates: ...` - Template file is missing
- `Unknown table name: invalid-table` - Invalid table placeholder name
- Markdown syntax errors - Invalid Markdown structure

## Adding New Templates

To add new template types:

1. Create a new Markdown file in `data/report_templates/`:
```markdown
# New Report Type - {{month_year}}

**Total Shaves:** {{total_shaves}}

## Content
{{tables.example-table}}
```

2. Update the code to use the new template
3. Add appropriate variables if needed
4. Update this documentation with the new variables

**Note**: With the unified architecture, adding new monthly report types is now simpler as they can leverage the existing `MonthlyReportGenerator` infrastructure.

## Best Practices

1. **Backup your templates**: Keep a backup of your custom templates
2. **Test changes**: Generate a test report after making template changes
3. **Use descriptive variable names**: Make variable names clear and meaningful
4. **Maintain formatting**: Preserve the Markdown formatting for proper report rendering
5. **Version control**: Consider adding your custom templates to version control
6. **Organize logically**: Group related tables together with descriptive headers
7. **Keep it readable**: Use clear section headers and logical flow
8. **Use shared templates**: Leverage the testing infrastructure to validate template changes
9. **Leverage unified architecture**: Use the consolidated generator for consistent behavior across report types

## Troubleshooting

### Template Not Found
- Check that the template directory exists at `data/report_templates/`
- Verify the template file name matches what the code expects
- Ensure the Markdown syntax is valid

### Table Placeholder Not Working
- Check that the table placeholder name is correct (see available placeholders above)
- Verify the table name uses hyphens, not underscores
- Ensure the table placeholder is properly formatted: `{{tables.table-name}}`

### Report Generation Fails
- This is expected behavior when templates are missing or invalid
- Check the template files for syntax errors
- Verify the template structure matches the expected format
- Look for clear error messages that indicate what's wrong

### Test Failures
- Ensure test templates in `tests/fixtures/report_template.yaml` are up to date
- Check that template changes don't break existing tests
- Verify that both unit and integration tests pass
- Run the unified monthly generator tests to ensure the new architecture is working correctly 