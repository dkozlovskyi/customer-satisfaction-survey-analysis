# Customer Satisfaction Survey Analysis Tool

A Python-based CLI tool for automated analysis of customer satisfaction surveys across multiple years. The tool reads CSV files from a local folder structure, performs comprehensive analysis including year-over-year comparisons, aggregations, and correlations, then outputs results as CSV files.

## Features

- **Automated Data Linking**: Links survey responses with company metadata via email domain
- **Per-Account Reports**: Generates individual CSV files for each customer account with comprehensive analysis
- **Individual Analysis**: Analyzes each respondent independently without aggregation to preserve unique perspectives
- **New Submissions Tracking**: Identifies first-time respondents with baseline deviation analysis
- **YoY Changes Analysis**: Tracks returning respondents with question-level deltas and group baselines
- **NPS & CSAT Tracking**: Monitors NPS status transitions and CSAT scores per respondent
- **Open-Ended Responses**: Captures all text responses in structured format
- **Statistical Aggregation**: Generates insights at question and question-group levels
- **Correlation Analysis**: Identifies strong relationships between different survey questions
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

**Columns Automatically Skipped (Non-Analytical):**
The following columns are automatically excluded from analysis if present:
- `Survey ID` - Survey instance identifier (no analytical value)
- `Response` - NPS explanation text (qualitative, not quantitative)
- `Sentiment` - Text representation of NPS metric (not analytical)
- `Industry Standard Question Type` - Question metadata (not response data)
- `Source` - Survey distribution method (not analytical)
- `Submission Name` - Submission title (not analytical)

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
- Non-analytical columns are automatically skipped

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
Aggregating by question...
  ✓ Created 28 question aggregates

Aggregating by question group...
  ✓ Created 12 question group aggregates

Calculating correlations...
  ✓ Calculated 156 correlations

Generating per-account reports...
  ✓ Wrote Acme_Corporation.csv
  ✓ Wrote TechStart.csv
  ✓ Wrote Global_Solutions_Inc.csv
  [... additional account files ...]
  ✓ Generated 25 account reports

  ✓ Wrote normalized_responses.csv
  ✓ Wrote question_aggregates.csv
  ✓ Wrote question_group_aggregates.csv
  ✓ Wrote correlations.csv
  ✓ Wrote unmatched_domains.csv

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

### Overview

The tool generates two types of outputs:

1. **Per-Account Reports**: Individual CSV files for each customer company (e.g., `Acme_Corporation.csv`, `TechStart.csv`)
2. **Global Analysis Files**: Cross-company aggregates and correlations

### Per-Account Reports (One file per customer)

Each customer account gets a dedicated CSV file named using the company name from `companies.csv`. These files contain 5 sections analyzing individual respondents without aggregation.

**File Naming:** Company names are sanitized (spaces → underscores, special characters removed) to create valid filenames.

#### Section 1: New Submissions

Identifies first-time respondents (present in current year but not previous year) with individual baseline analysis.

**Purpose:** Understand new respondents' satisfaction levels and identify areas where they score particularly low.

**Format:** One row per new respondent with all questions as columns (horizontal layout).

**Columns:**
- `Email` - Respondent email
- `First Name` - Respondent first name
- `Last Name` - Respondent last name
- `Individual Baseline (Std Dev)` - Standard deviation of this person's answers (their personal variability)
- `Lowest Score` - Minimum score across all their answers
- `Highest Score` - Maximum score across all their answers
- `Count Scores <8` - Number of questions where they scored below 8
- `[Question 1]` - Answer to first question (e.g., "Customer Satisfaction Rating")
- `[Question 2]` - Answer to second question (e.g., "Team Delivery Timeliness Rating")
- ... (additional columns for each question)

**Key Insights:**
- Each row = one new respondent with all their answers visible at a glance
- Quickly identify respondents with multiple low scores (Count Scores <8)
- Spot patterns across questions in a single row
- Compare baseline variability across new respondents

#### Section 2: YoY Changes

Tracks returning respondents (present in both years) with question-level deltas and group-based baseline analysis.

**Purpose:** Identify improvement or decline in satisfaction for returning respondents, using question group baselines to detect unusual changes.

**Columns:**
- `Email` - Respondent email
- `First Name` - Respondent first name
- `Last Name` - Respondent last name
- `Question Group` - Question group (e.g., "Team Performance")
- `Question` - Question short form
- `{prev_year} Value` - Score in previous year
- `{curr_year} Value` - Score in current year
- `Delta` - Change (current - previous)
- `Group Baseline (Std Dev)` - Standard deviation of deltas within this question group (across all account respondents)
- `Strong Deviation (>baseline)` - "yes" if |delta| exceeds group baseline
- `Large Absolute Change (>1)` - "yes" if |delta| > 1

**Key Insights:**
- Focus on deltas that exceed typical variability for the question group
- Identify absolute changes > 1 point (always significant)
- Track which respondents improved vs declined

#### Section 3: NPS Status and Transitions

Monitors NPS (Net Promoter Score) classification and year-over-year transitions.

**Purpose:** Track NPS category changes (Detractor → Passive → Promoter) to identify satisfaction trajectory.

**NPS Classification:**
- **Promoter**: Score 9-10
- **Passive**: Score 7-8
- **Detractor**: Score 0-6

**Columns:**
- `Email` - Respondent email
- `First Name` - Respondent first name
- `Last Name` - Respondent last name
- `{prev_year} NPS Score` - NPS score in previous year (or N/A)
- `{prev_year} Status` - NPS category in previous year
- `{curr_year} NPS Score` - NPS score in current year
- `{curr_year} Status` - NPS category in current year
- `Status Change` - "yes" if category changed, "no" if same, "N/A" if not applicable
- `Category Transition` - Description of transition (e.g., "Detractor → Promoter") or "No change"

**Key Insights:**
- Identify promoters at risk of becoming passive/detractors
- Celebrate detractors who became promoters
- Track overall NPS trajectory per respondent

#### Section 4: CSAT Status

Current Customer Satisfaction (CSAT) score for each respondent.

**Purpose:** Simple view of current satisfaction levels per respondent.

**Columns:**
- `Email` - Respondent email
- `First Name` - Respondent first name
- `Last Name` - Respondent last name
- `CSAT Score` - Current year CSAT score

**Key Insights:**
- Quick reference for current satisfaction
- No aggregation - each respondent's individual score
- Useful for account manager follow-up

#### Section 5: Open Answers

All open-ended text responses for current year.

**Purpose:** Capture qualitative feedback and suggestions.

**Columns:**
- `Email` - Respondent email
- `First Name` - Respondent first name
- `Last Name` - Respondent last name
- `[Question 1]` - Answer to first open-ended question
- `[Question 2]` - Answer to second open-ended question
- ... (additional columns for each open-ended question found)

**Key Insights:**
- Qualitative context for numeric scores
- Specific suggestions and feedback
- Identify themes across respondents

---

### Global Analysis Files

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

### 2. question_aggregates.csv

Statistical aggregation by question with 2024/2025 comparison and statistical significance detection.

**Important:** Only shows 2025 year rows with 2024 data in separate columns for easy comparison.

**Columns:**
- `year` - Always 2025 (current year)
- `question_short_form` - Question identifier
- `question_group` - Question group
- `2024_response_count` - Number of responses in 2024 (N/A if question didn't exist)
- `2024_mean` - Average score in 2024
- `2024_median` - Median score in 2024
- `2024_std_dev` - Standard deviation in 2024
- `2025_response_count` - Number of responses in 2025
- `2025_mean` - Average score in 2025
- `2025_median` - Median score in 2025
- `2025_std_dev` - Standard deviation in 2025
- `2025_delta` - Change in mean from 2024 to 2025 (2025 mean - 2024 mean)
- `2025_std_dev_group_deltas` - Standard deviation of deltas within the question group
- `significant_change` - "yes" if change meets significance criteria, otherwise "no"

**Significance Detection Logic:**

For each question group, the tool calculates the standard deviation of deltas within the group.

A question's change is marked as "yes" (significant) if **either** condition is met:
1. |question_delta| ≥ 0.5 (absolute change of 0.5 points or more), **OR**
2. |question_delta| > group_std_dev_delta (exceeds typical group variability)

This dual-criteria approach ensures that:
- Large changes (≥0.5 points) are always flagged as significant
- Smaller changes that are unusual for their group are also detected

**Use Cases:**
- Quick 2024 vs 2025 comparison in single view
- Identify questions with statistically significant changes
- Focus attention on outlier improvements or declines
- Understand which changes are meaningful vs normal variation
- Track year-over-year improvements or declines

### 3. question_group_aggregates.csv

Statistical aggregation by question group with 2024/2025 comparison and survey type-based significance detection.

**Important:** Only shows 2025 year rows with 2024 data in separate columns for easy comparison.

**Columns:**
- `year` - Always 2025 (current year)
- `question_group` - Question group name
- `survey_type` - Survey type the group belongs to (Team-Level or Company-Level)
- `2024_response_count` - Number of responses in 2024
- `2024_mean` - Average score in 2024
- `2024_median` - Median score in 2024
- `2024_std_dev` - Standard deviation in 2024
- `2025_response_count` - Number of responses in 2025
- `2025_mean` - Average score in 2025
- `2025_median` - Median score in 2025
- `2025_std_dev` - Standard deviation in 2025
- `2025_delta` - Change in mean from 2024 to 2025
- `2025_std_dev_survey_type_deltas` - Standard deviation of deltas within the survey type (Team-Level or Company-Level)
- `significant_change` - "yes" if change meets significance criteria, otherwise "no"

**Significance Detection Logic:**

For each survey type (Team-Level or Company-Level), the tool calculates the standard deviation of deltas across all question groups in that survey type.

A question group's change is marked as "yes" (significant) if **either** condition is met:
1. |group_delta| ≥ 0.5 (absolute change of 0.5 points or more), **OR**
2. |group_delta| > survey_type_std_dev_delta (exceeds typical variability for that survey type)

This helps identify question groups with unusual changes compared to other groups in the same survey type.

**Use Cases:**
- High-level performance overview
- Compare broad areas (e.g., "Team Performance" vs "Customer Satisfaction")
- Track year-over-year trends at group level
- Identify which question groups changed significantly
- Executive summaries

### 4. correlations.csv

Strong Pearson correlation coefficients between numeric questions (latest year only).

**Important:** Only correlations with |r| ≥ 0.7 (Strong) are included in this file.

**Columns:**
- `year` - Survey year (latest year only)
- `segment_type` - Type of segmentation (Overall, Region, Tenure)
- `segment_value` - Specific segment (All, US, Canada, Rest of the World, >4 years, ≤4 years)
- `question_1` - First question
- `question_2` - Second question
- `correlation` - Pearson correlation coefficient (range: -1 to 1, filtered to |r| ≥ 0.7)
- `n_pairs` - Number of paired responses
- `interpretation` - Always "Strong" (only strong correlations are included)

**Segmentation:**
- **Overall**: All responses combined
- **Region**: US, Canada, Rest of the World (includes Europe, Asia Pacific, Latin America, Other)
- **Tenure**: >4 years (established clients), ≤4 years (newer clients)

**Correlation Strength:**
- **Strong** (|r| ≥ 0.7): Strong relationship - Only these are included in the output

**Methodological Cautions:**
- Correlation ≠ causation
- Minimum 3 paired responses required per segment
- Consider sample size when interpreting
- Be aware of confounding variables
- Only calculated for latest year to focus on current trends

**Use Cases:**
- Identify related satisfaction drivers
- Understand which areas move together
- Compare correlation patterns across regions and tenure groups
- Hypothesis generation for deeper analysis

### 5. unmatched_domains.csv

Full customer details for respondents whose email domains couldn't be matched to companies.

**Note:** This file is only created if there are unmatched domains. If all respondents match companies, this file won't exist.

**Columns:**
- `email` - Respondent email address
- `first_name` - Respondent first name
- `last_name` - Respondent last name
- `domain` - Email domain (extracted from email)
- `response_count` - Number of survey responses from this customer

**Use Cases:**
- Identify missing companies in metadata
- Contact information for manual company lookup
- Update companies.csv for future runs
- Data quality improvement

### 6. unknown_questions.csv

Question columns in responses not found in questions.csv metadata.

**Note:** This file is only created if there are unknown questions. If all question columns are recognized, this file won't exist.

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
│  - Account      │
│    reports (5   │
│    sections)    │
│  - Aggregations │
│  - Correlations │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Output CSVs    │
│  - Per-account  │
│    files        │
│  - Global files │
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

### Adding New Account Report Sections

Add new sections to per-account reports by creating a new method:

```python
def _write_custom_section(self, writer, responses, curr_year):
    """Write a custom analysis section"""
    writer.writerow(['### CUSTOM SECTION ###'])
    writer.writerow(['Description of analysis'])
    writer.writerow([])
    # ... your analysis logic ...

# Then call it from _write_account_report():
self._write_custom_section(writer, responses, curr_year)
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
