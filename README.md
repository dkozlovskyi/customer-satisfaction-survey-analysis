# Customer Satisfaction Survey Analysis Tool

A Python-based CLI tool for automated analysis of customer satisfaction surveys across multiple years. The tool reads CSV files from a local folder structure, performs comprehensive analysis including year-over-year comparisons, aggregations, and correlations, then outputs results as CSV files.

## Features

- **Automated Data Linking**: Links survey responses with company metadata via email domain
- **Year-over-Year Analysis**: Calculates deltas at respondent/question level
- **Multi-Level Aggregation**: Generates insights at question, question-group, and segment levels
- **Correlation Analysis**: Identifies relationships between different survey questions
- **Comprehensive Output**: Produces clean CSV files ready for visualization in spreadsheet tools
- **Validation & Error Tracking**: Tracks unmatched domains and unknown questions

## Requirements

- Python 3.7 or higher
- Standard library only (no external dependencies)

## Installation

1. Clone or download this repository
2. Ensure Python 3.7+ is installed:
   ```bash
   python --version
   ```

## Folder Structure

The tool requires a specific input folder structure:

```
input/
├── meta/
│   ├── questions.csv        # Question metadata
│   └── companies.csv        # Company metadata
│
└── responses/
    ├── previous/
    │   └── Responses_2024.csv   # Previous year responses
    └── current/
        └── Responses_2025.csv   # Current year responses
```

**Important Notes:**
- The year is automatically extracted from filenames (e.g., `Responses_2024.csv` → year = 2024)
- You can have multiple response files in each directory
- The tool validates the structure on startup and will fail with clear errors if files are missing

## Input File Schemas

### 1. questions.csv (Meta)

Defines all survey questions and their metadata.

**Required Columns:**
- `Short Form` - Short identifier used as column name in response files (e.g., "Team Delivery Timeliness Rating")
- `Introduced` - Year when question was introduced (e.g., 2024)
- `Survey Type` - Either "Team-Level" or "Company-Level"
- `Question Group` - Logical grouping (e.g., "Team Performance", "Customer Satisfaction")
- `Original Question` - Full question text shown to respondents

**Example:**
```csv
Short Form,Introduced,Survey Type,Question Group,Original Question
Team Delivery Timeliness Rating,2024,Team-Level,Team Performance,How satisfied are you with the timeliness of team deliveries?
Customer Satisfaction Rating,2024,Company-Level,Customer Satisfaction,Overall how satisfied are you with our services?
```

### 2. companies.csv (Meta)

Contains metadata about customer companies for segmentation and correlation analysis.

**Required Columns:**
- `Domain` - Company email domain (e.g., "acme.com")
- `Company` - Company name

**Optional Columns:**
- `Services` - Services provided
- `Revenue share` - Revenue contribution
- `Region` - Geographic region
- `First Interaction Date` - When engagement started
- `Tenure (mo.)` - Tenure in months
- `Tenure (years)` - Tenure in years
- `Collaboration Type` - Type of engagement
- `Continious collaboration` - Ongoing status
- `Engagement Source` - How client was acquired
- `Notes` - Additional notes

**Example:**
```csv
Domain,Company,Region,Tenure (years),Services,Revenue share
acme.com,Acme Corp,North America,3.5,Software Development,15%
techco.io,TechCo,Europe,1.2,Consulting,8%
```

### 3. Responses_YYYY.csv

Survey responses for a specific year.

**Required Columns:**
- `Record ID` - Unique response identifier
- `Email` - Respondent email (used for domain extraction)
- `Contact first name` - Respondent first name
- `Contact last name` - Respondent last name
- `Date` - Response date
- `Survey Type` - "Team-Level" or "Company-Level"

**Question Columns:**
All other columns are treated as question responses. Column names must match the `Short Form` values in questions.csv.

**Example:**
```csv
Record ID,Email,Contact first name,Contact last name,Date,Survey Type,Team Delivery Timeliness Rating,Customer Satisfaction Rating
R001,john@acme.com,John,Doe,2024-03-15,Company-Level,5,4
R002,jane@techco.io,Jane,Smith,2024-03-16,Team-Level,4,
```

**Notes:**
- Numeric ratings: Values like 1-5 ratings are automatically detected and parsed
- Text responses: Open-ended answers are kept as text
- Company-Level surveys include additional questions not in Team-Level surveys
- Empty values are ignored

## Usage

### Basic Usage

From the project directory:

```bash
python survey_analyzer.py
```

This uses default paths:
- Input: `./input`
- Output: `./output`

### Custom Paths

```bash
python survey_analyzer.py --input /path/to/input --output /path/to/output
```

### What Happens During Execution

1. **Validation**: Checks folder structure and required files
2. **Loading**: Reads all metadata and response files
3. **Linking**: Matches responses to companies via email domain
4. **Normalization**: Converts wide format to long format
5. **Analysis**: Calculates deltas, aggregations, and correlations
6. **Output**: Generates CSV files in output directory

### Example Output

```
============================================================
Customer Satisfaction Survey Analysis Tool
============================================================
Input directory:  ./input
Output directory: ./output
============================================================

Validating input folder structure...
  ✓ Found: input/meta
  ✓ Found: input/responses/previous
  ✓ Found: input/responses/current
  ✓ Found: input/meta/questions.csv
  ✓ Found: input/meta/companies.csv
  ✓ Found 1 previous response file(s)
  ✓ Found 1 current response file(s)
✓ Folder structure validated successfully

Loading question metadata...
  ✓ Loaded 14 questions

Loading company metadata...
  ✓ Loaded 25 companies

Loading survey responses...
  Loading Responses_2024.csv (year: 2024)...
  Loading Responses_2025.csv (year: 2025)...
  ✓ Loaded 150 total responses

Normalizing responses and linking with companies...
  ✓ Created 1800 normalized records
  ✓ Matched 140 responses to companies
  ✓ 10 responses without company match

Generating output files...
Calculating year-over-year deltas...
  ✓ Calculated 350 year-over-year deltas

Aggregating by question...
  ✓ Created 28 question aggregates

Aggregating by question group...
  ✓ Created 12 question group aggregates

Aggregating by segment...
  ✓ Created 85 segment aggregates

Calculating correlations...
  ✓ Calculated 156 correlations

  ✓ Wrote normalized_responses.csv
  ✓ Wrote yoy_deltas.csv
  ✓ Wrote question_aggregates.csv
  ✓ Wrote question_group_aggregates.csv
  ✓ Wrote segment_aggregates.csv
  ✓ Wrote correlations.csv
  ✓ Wrote unmatched_domains.csv
  ✓ Wrote unknown_questions.csv

✓ All output files generated in: output

============================================================
ANALYSIS SUMMARY
============================================================
Total responses read:        150
Matched to companies:        140
Unmatched domains:           10
Numeric answers:             1600
Text answers:                200
Normalized records created:  1800
Unknown questions found:     0
============================================================

✓ Analysis completed successfully!
```

## Output Files

All outputs are generated in the `output/` directory (or custom path specified).

### 1. normalized_responses.csv

Long-format normalized data with all responses and linked metadata.

**Columns:**
- `year` - Survey year
- `record_id` - Response record ID
- `email` - Respondent email
- `first_name` - Respondent first name
- `last_name` - Respondent last name
- `respondent_domain` - Extracted email domain
- `account_domain` - Matched company domain (from companies.csv)
- `company_name` - Matched company name
- `region` - Company region
- `tenure_years` - Company tenure in years
- `survey_type` - Team-Level or Company-Level
- `question_short_form` - Question identifier
- `question_group` - Question grouping
- `original_question` - Full question text
- `answer_raw` - Raw answer value
- `answer_numeric` - Parsed numeric value (if applicable)
- `is_numeric` - Whether answer is numeric (True/False)

**Use Cases:**
- Base data for custom analysis
- Filtering specific respondents or questions
- Data quality validation

### 2. yoy_deltas.csv

Year-over-year changes at the respondent/question level (numeric questions only).

**Columns:**
- `email` - Respondent email
- `company_name` - Company name
- `question_short_form` - Question identifier
- `question_group` - Question group
- `previous_year` - Earlier year
- `previous_value` - Score in earlier year
- `current_year` - Later year
- `current_value` - Score in later year
- `delta` - Absolute change (current - previous)
- `delta_pct` - Percentage change

**Use Cases:**
- Identify respondents with improved/declined sentiment
- Track individual company progress
- Flag significant changes for follow-up

### 3. question_aggregates.csv

Statistical aggregation by question and year.

**Columns:**
- `year` - Survey year
- `question_short_form` - Question identifier
- `question_group` - Question group
- `response_count` - Number of responses
- `mean` - Average score
- `median` - Median score
- `std_dev` - Standard deviation
- `min` - Minimum score
- `max` - Maximum score

**Use Cases:**
- Compare question performance across years
- Identify highest/lowest rated areas
- Understand score distribution

### 4. question_group_aggregates.csv

Statistical aggregation by question group and year.

**Columns:**
- `year` - Survey year
- `question_group` - Question group name
- `response_count` - Number of responses
- `mean` - Average score across all questions in group
- `median` - Median score
- `std_dev` - Standard deviation
- `min` - Minimum score
- `max` - Maximum score

**Use Cases:**
- High-level performance overview
- Compare broad areas (e.g., "Team Performance" vs "Customer Satisfaction")
- Executive summaries

### 5. segment_aggregates.csv

Aggregation by customer segments (region, survey type).

**Columns:**
- `year` - Survey year
- `segment_type` - Type of segmentation (e.g., "Region", "Survey Type")
- `segment_value` - Specific segment (e.g., "North America", "Team-Level")
- `question_short_form` - Question identifier
- `response_count` - Number of responses in segment
- `mean` - Average score for segment
- `median` - Median score for segment

**Use Cases:**
- Compare regional performance
- Identify segment-specific issues
- Targeted improvement initiatives

### 6. correlations.csv

Pearson correlation coefficients between numeric questions.

**Columns:**
- `year` - Survey year
- `question_1` - First question
- `question_2` - Second question
- `correlation` - Pearson correlation coefficient (-1 to 1)
- `n_pairs` - Number of paired responses
- `interpretation` - Qualitative strength (Very Weak, Weak, Moderate, Strong)

**Interpretation Guide:**
- **Strong** (|r| ≥ 0.7): Strong relationship
- **Moderate** (0.4 ≤ |r| < 0.7): Moderate relationship
- **Weak** (0.2 ≤ |r| < 0.4): Weak relationship
- **Very Weak** (|r| < 0.2): Very weak relationship

**Methodological Cautions:**
- Correlation ≠ causation
- Minimum 3 paired responses required
- Consider sample size when interpreting
- Be aware of confounding variables

**Use Cases:**
- Identify related satisfaction drivers
- Understand which areas move together
- Hypothesis generation for deeper analysis

### 7. unmatched_domains.csv

Email domains that couldn't be matched to companies.

**Columns:**
- `domain` - Email domain
- `occurrences` - Number of responses from this domain

**Use Cases:**
- Identify missing companies in metadata
- Update companies.csv for future runs
- Data quality improvement

### 8. unknown_questions.csv

Question columns in responses not found in questions.csv metadata.

**Columns:**
- `question_column` - Column name from response files
- `occurrences` - Number of occurrences

**Use Cases:**
- Identify metadata gaps
- Update questions.csv for future runs
- Catch typos or renamed questions

## Data Flow

```
┌─────────────────┐
│  Input CSVs     │
│  - questions    │
│  - companies    │
│  - responses    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Validation     │
│  - Structure    │
│  - Files exist  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Loading   │
│  - Parse CSVs   │
│  - Extract year │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Linking        │
│  - Email domain │
│  - Join company │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Normalization  │
│  - Wide → Long  │
│  - Parse numeric│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Analysis       │
│  - YoY deltas   │
│  - Aggregations │
│  - Correlations │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Output CSVs    │
│  - 8 files      │
└─────────────────┘
```

## Error Handling

The tool validates inputs and provides clear error messages:

- **Missing folders/files**: Indicates exactly which path is missing
- **Invalid year format**: If filename doesn't contain a 4-digit year
- **Empty CSVs**: Warns if required files are empty
- **Unmatched domains**: Logged in `unmatched_domains.csv` rather than failing
- **Unknown questions**: Logged in `unknown_questions.csv` with "Unknown" group

## Best Practices

1. **Data Preparation**
   - Ensure email domains in companies.csv match actual respondent domains
   - Normalize domains to lowercase
   - Keep question short forms consistent across years

2. **Question Metadata**
   - Update questions.csv whenever new questions are added
   - Set correct "Introduced" year for proper filtering
   - Use meaningful question groups for better aggregation

3. **Iterative Analysis**
   - Review unmatched_domains.csv and update companies.csv
   - Review unknown_questions.csv and update questions.csv
   - Re-run for complete results

4. **Correlation Interpretation**
   - Focus on correlations with sufficient sample size (n_pairs > 30)
   - Remember correlation doesn't imply causation
   - Use correlations for hypothesis generation, not conclusions

## Extending the Tool

The tool is designed to be extensible. Common customizations:

### Adding New Segments

Edit the `aggregate_by_segment()` method to add new segmentation dimensions:

```python
# By Collaboration Type
groups = defaultdict(list)
for resp in self.normalized_responses:
    if resp.is_numeric and resp.collaboration_type:
        key = (resp.year, 'Collaboration Type', resp.collaboration_type, resp.question_short_form)
        groups[key].append(resp.answer_numeric)
```

### Custom Statistical Measures

Extend the `Stats` dataclass and `calculate_stats()` method:

```python
@dataclass
class Stats:
    # ... existing fields ...
    percentile_90: float = 0.0

def calculate_stats(self, values: List[float]) -> Stats:
    # ... existing code ...
    stats.percentile_90 = statistics.quantiles(values, n=10)[8] if len(values) >= 10 else 0
    return stats
```

### Additional Output Formats

Add methods to export to JSON, Excel, or databases:

```python
def _write_json_output(self, data: List[Dict], filename: str):
    import json
    with open(self.output_dir / filename, 'w') as f:
        json.dump(data, f, indent=2)
```

## Troubleshooting

### "Required directory not found"
- Verify folder structure matches the expected layout
- Check that `input/meta`, `input/responses/previous`, and `input/responses/current` all exist

### "Could not extract year from filename"
- Ensure response files contain a 4-digit year (e.g., `Responses_2024.csv`)
- Year must be in the filename, not just the folder

### "No CSV files found in responses"
- Verify CSV files exist in the `previous/` and `current/` subdirectories
- Check file extensions are `.csv` (lowercase)

### High number of unmatched domains
- Review `unmatched_domains.csv`
- Add missing companies to `companies.csv`
- Ensure domain field uses lowercase and matches email domains exactly

### Missing questions in output
- Check `unknown_questions.csv`
- Add missing questions to `questions.csv`
- Verify column names in response files match `Short Form` in questions.csv

## License

This tool is provided as-is for analysis of customer satisfaction surveys.

## Support

For issues or questions:
1. Check this README
2. Review error messages carefully
3. Validate input file schemas
4. Check the generated diagnostic files (unmatched_domains.csv, unknown_questions.csv)
