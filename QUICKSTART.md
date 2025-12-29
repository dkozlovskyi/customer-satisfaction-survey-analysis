# Quick Start Guide

Get started with the Customer Satisfaction Survey Analysis Tool in 3 simple steps.

## Step 1: Verify Requirements

Ensure you have Python 3.7 or higher:

```bash
python --version
```

## Step 2: Prepare Your Data

The tool includes sample data to help you get started. The required folder structure is:

```
input/
├── meta/
│   ├── questions.csv        # Your survey questions
│   └── companies.csv        # Your customer companies
└── responses/
    ├── previous/
    │   └── Responses_2024.csv   # Previous year data
    └── current/
        └── Responses_2025.csv   # Current year data
```

### Using Sample Data

Sample data is already included in the `input/` folder. You can run the tool immediately to see how it works!

### Using Your Own Data

Replace the sample files with your own CSV files following these schemas:

**questions.csv:**
```csv
Short Form,Introduced,Survey Type,Question Group,Original Question
Team Delivery Rating,2024,Team-Level,Performance,How satisfied are you...
```

**companies.csv:**
```csv
Domain,Company,Region,Tenure (years)
acme.com,Acme Corp,North America,3.5
```

**Responses_YYYY.csv:**
```csv
Record ID,Email,Contact first name,Contact last name,Date,Survey Type,Team Delivery Rating
R001,john@acme.com,John,Doe,2024-03-15,Company-Level,5
```

**Important:** The year MUST be in the filename (e.g., `Responses_2024.csv`)

## Step 3: Run the Analysis

From the project directory:

```bash
python survey_analyzer.py
```

That's it! The tool will:
- Validate your input files
- Link responses with companies
- Calculate year-over-year changes
- Generate 8 output CSV files in the `output/` folder

## Understanding the Output

After running, check the `output/` folder for these files:

| File | What it contains |
|------|------------------|
| `normalized_responses.csv` | All survey data in long format with company metadata |
| `yoy_deltas.csv` | Year-over-year changes for each respondent/question |
| `question_aggregates.csv` | Average scores by question |
| `question_group_aggregates.csv` | Average scores by question group |
| `segment_aggregates.csv` | Average scores by region/segment |
| `correlations.csv` | Relationships between different questions |
| `unmatched_domains.csv` | Email domains not found in companies.csv |
| `unknown_questions.csv` | Question columns not found in questions.csv |

## Next Steps

1. **Review diagnostics:**
   - Check `unmatched_domains.csv` and add missing companies to `companies.csv`
   - Check `unknown_questions.csv` and add missing questions to `questions.csv`
   - Re-run for complete results

2. **Analyze results:**
   - Import CSV files into Google Sheets or Excel
   - Create visualizations (charts, graphs)
   - Share insights with stakeholders

3. **Customize:**
   - See README.md for advanced customization options
   - Add your own segments or statistical measures
   - Export to different formats

## Example Analysis Workflow

```bash
# 1. Initial run with sample data
python survey_analyzer.py

# 2. Review unmatched domains
cat output/unmatched_domains.csv

# 3. Update companies.csv with missing domains
# Edit input/meta/companies.csv

# 4. Re-run for complete analysis
python survey_analyzer.py

# 5. Open results in spreadsheet tool
# Import output/*.csv into Google Sheets
```

## Common Use Cases

**Track Customer Satisfaction Trends:**
```bash
# Look at question_aggregates.csv
# Compare mean scores between years
```

**Identify At-Risk Customers:**
```bash
# Look at yoy_deltas.csv
# Filter for negative deltas
# Sort by delta_pct to find biggest drops
```

**Understand Regional Differences:**
```bash
# Look at segment_aggregates.csv
# Filter segment_type = "Region"
# Compare means across regions
```

**Find Related Satisfaction Drivers:**
```bash
# Look at correlations.csv
# Focus on "Strong" or "Moderate" correlations
# Identify questions that move together
```

## Troubleshooting

**"Required directory not found"**
- Run `ls input/meta` to verify folders exist
- Create missing folders manually if needed

**"Could not extract year from filename"**
- Ensure response files have format: `Responses_2024.csv`
- Year must be 4 digits in the filename

**Many unmatched domains**
- This is normal on first run
- Add companies to `companies.csv`
- Ensure Domain column matches email domains exactly (lowercase)

**No year-over-year deltas**
- Ensure you have overlapping respondents (same email) across years
- Check that both years have data in responses/previous/ and responses/current/

## Custom Paths

Run with custom input/output directories:

```bash
python survey_analyzer.py --input /path/to/data --output /path/to/results
```

## Getting Help

- Full documentation: See README.md
- Input file schemas: See README.md "Input File Schemas"
- Output descriptions: See README.md "Output Files"
- Extending the tool: See README.md "Extending the Tool"

---

Happy analyzing! 🚀
