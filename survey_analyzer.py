#!/usr/bin/env python3
"""
Customer Satisfaction Survey Analysis Tool

Analyzes survey responses across multiple years, links with company metadata,
calculates year-over-year deltas, and generates aggregated insights.

Usage:
    python survey_analyzer.py [--input INPUT_DIR] [--output OUTPUT_DIR]
"""

import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import statistics


# ============================================================
# CONSTANTS
# ============================================================

# CSV Column Names
class CSVColumns:
    """Standard CSV column names for input files"""
    RECORD_ID = 'Record ID'
    EMAIL = 'Email'
    FIRST_NAME = 'Contact first name'
    LAST_NAME = 'Contact last name'
    DATE = 'Date'
    SURVEY_TYPE = 'Survey Type'

    # Columns to skip during processing
    SKIP_COLS = {
        'Survey ID',  # Survey instance ID - no analytical value
        'Response',  # NPS explanation - qualitative only
        'Sentiment',  # Text representation of NPS - skip
        'Industry Standard Question Type',  # Question type metadata - skip
        'Source',  # Survey distribution method - skip
        'Submission Name'  # Submission title - skip
    }

    STANDARD_COLS = {RECORD_ID, EMAIL, FIRST_NAME, LAST_NAME, DATE, SURVEY_TYPE}


# Analysis Thresholds
class Thresholds:
    """Thresholds used in analysis"""
    MIN_CORRELATION_PAIRS = 3  # Minimum pairs needed for correlation calculation
    STRONG_CORRELATION = 0.7  # Threshold for strong correlation


# File Paths
class Paths:
    """Standard directory and file paths"""
    META = 'meta'
    RESPONSES = 'responses'
    PREVIOUS = 'previous'
    CURRENT = 'current'
    QUESTIONS_CSV = 'questions.csv'
    COMPANIES_CSV = 'companies.csv'


@dataclass
class Question:
    """Represents a survey question from metadata"""
    short_form: str
    introduced: int
    survey_type: str
    question_group: str
    original_question: str


@dataclass
class Company:
    """Represents a company from metadata"""
    domain: str
    company: str
    services: str = ""
    revenue_share: str = ""
    region: str = ""
    first_interaction_date: str = ""
    tenure_months: str = ""
    tenure_years: str = ""
    collaboration_type: str = ""
    continuous_collaboration: str = ""
    engagement_source: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Company':
        """Create Company from CSV row dict"""
        return cls(
            domain=data.get('Domain', '').strip().lower(),
            company=data.get('Company', '').strip(),
            services=data.get('Services', '').strip(),
            revenue_share=data.get('Revenue share', '').strip(),
            region=data.get('Region', '').strip(),
            first_interaction_date=data.get('First Interaction Date', '').strip(),
            tenure_months=data.get('Tenure (mo.)', '').strip(),
            tenure_years=data.get('Tenure (years)', '').strip(),
            collaboration_type=data.get('Collaboration Type', '').strip(),
            continuous_collaboration=data.get('Continious collaboration', '').strip(),
            engagement_source=data.get('Engagement Source', '').strip(),
            notes=data.get('Notes', '').strip()
        )


@dataclass
class Response:
    """Represents a single survey response (wide format)"""
    year: int
    record_id: str
    email: str
    first_name: str
    last_name: str
    date: str
    survey_type: str
    answers: Dict[str, str]  # question -> answer mapping


@dataclass
class NormalizedResponse:
    """Represents a normalized response in long format"""
    year: int
    record_id: str
    email: str
    first_name: str
    last_name: str
    respondent_domain: str
    account_domain: str
    company_name: str
    region: str
    tenure_years: str
    survey_type: str
    question_short_form: str
    question_group: str
    original_question: str
    answer_raw: str
    answer_numeric: Optional[float] = None
    is_numeric: bool = False


@dataclass
class Stats:
    """Statistical measures for a group of numeric values"""
    count: int = 0
    mean: float = 0.0
    median: float = 0.0
    std_dev: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0


class SurveyAnalyzer:
    """Main analyzer class"""

    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

        # Data containers
        self.questions: Dict[str, Question] = {}
        self.companies: Dict[str, Company] = {}  # domain -> Company
        self.responses: List[Response] = []
        self.normalized_responses: List[NormalizedResponse] = []

        # Tracking
        self.unmatched_domains: Set[str] = set()
        self.unknown_questions: Set[str] = set()

        # Statistics
        self.stats = {
            'rows_read': 0,
            'matched_companies': 0,
            'unmatched_domains': 0,
            'numeric_answers': 0,
            'text_answers': 0
        }

    def validate_structure(self) -> None:
        """Validate input folder structure and required files"""
        print("Validating input folder structure...")

        # Check main directories
        required_dirs = [
            self.input_dir / Paths.META,
            self.input_dir / Paths.RESPONSES / Paths.PREVIOUS,
            self.input_dir / Paths.RESPONSES / Paths.CURRENT
        ]

        for dir_path in required_dirs:
            if not dir_path.exists():
                raise FileNotFoundError(f"Required directory not found: {dir_path}")
            print(f"  ✓ Found: {dir_path}")

        # Check required files
        required_files = [
            self.input_dir / Paths.META / Paths.QUESTIONS_CSV,
            self.input_dir / Paths.META / Paths.COMPANIES_CSV
        ]

        for file_path in required_files:
            if not file_path.exists():
                raise FileNotFoundError(f"Required file not found: {file_path}")
            print(f"  ✓ Found: {file_path}")

        # Check for response files
        prev_files = list((self.input_dir / Paths.RESPONSES / Paths.PREVIOUS).glob('*.csv'))
        curr_files = list((self.input_dir / Paths.RESPONSES / Paths.CURRENT).glob('*.csv'))

        if not prev_files:
            raise FileNotFoundError("No CSV files found in input/responses/previous/")
        if not curr_files:
            raise FileNotFoundError("No CSV files found in input/responses/current/")

        print(f"  ✓ Found {len(prev_files)} previous response file(s)")
        print(f"  ✓ Found {len(curr_files)} current response file(s)")

        print("✓ Folder structure validated successfully\n")

    def load_questions(self) -> None:
        """Load question metadata"""
        print("Loading question metadata...")
        file_path = self.input_dir / Paths.META / Paths.QUESTIONS_CSV

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                question = Question(
                    short_form=row['Short Form'].strip(),
                    introduced=int(row['Introduced']),
                    survey_type=row['Survey Type'].strip(),
                    question_group=row['Question Group'].strip(),
                    original_question=row['Original Question'].strip()
                )
                self.questions[question.short_form] = question

        print(f"  ✓ Loaded {len(self.questions)} questions\n")

    def load_companies(self) -> None:
        """Load company metadata"""
        print("Loading company metadata...")
        file_path = self.input_dir / Paths.META / Paths.COMPANIES_CSV

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                company = Company.from_dict(row)
                if company.domain:
                    self.companies[company.domain] = company

        print(f"  ✓ Loaded {len(self.companies)} companies\n")

    def extract_year_from_filename(self, filename: str) -> int:
        """Extract year from filename like 'Responses_2024.csv'"""
        match = re.search(r'(\d{4})', filename)
        if match:
            return int(match.group(1))
        raise ValueError(f"Could not extract year from filename: {filename}")

    def load_responses(self) -> None:
        """Load all response files"""
        print("Loading survey responses...")

        # Load previous year responses
        prev_dir = self.input_dir / Paths.RESPONSES / Paths.PREVIOUS
        for file_path in prev_dir.glob('*.csv'):
            year = self.extract_year_from_filename(file_path.name)
            self._load_response_file(file_path, year)

        # Load current year responses
        curr_dir = self.input_dir / Paths.RESPONSES / Paths.CURRENT
        for file_path in curr_dir.glob('*.csv'):
            year = self.extract_year_from_filename(file_path.name)
            self._load_response_file(file_path, year)

        self.stats['rows_read'] = len(self.responses)
        print(f"  ✓ Loaded {len(self.responses)} total responses\n")

    def _load_response_file(self, file_path: Path, year: int) -> None:
        """Load a single response file"""
        print(f"  Loading {file_path.name} (year: {year})...")

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Extract standard fields
                response = Response(
                    year=year,
                    record_id=row.get(CSVColumns.RECORD_ID, '').strip(),
                    email=row.get(CSVColumns.EMAIL, '').strip(),
                    first_name=row.get(CSVColumns.FIRST_NAME, '').strip(),
                    last_name=row.get(CSVColumns.LAST_NAME, '').strip(),
                    date=row.get(CSVColumns.DATE, '').strip(),
                    survey_type=row.get(CSVColumns.SURVEY_TYPE, '').strip(),
                    answers={}
                )

                # Extract question answers (skip standard and non-analytical columns)
                for col, value in row.items():
                    if col not in CSVColumns.STANDARD_COLS and col not in CSVColumns.SKIP_COLS and value.strip():
                        response.answers[col] = value.strip()

                self.responses.append(response)

    def extract_domain(self, email: str) -> str:
        """Extract domain from email address"""
        if '@' in email:
            return email.split('@')[1].strip().lower()
        return ''

    def normalize_responses(self) -> None:
        """Convert responses from wide to long format and link with companies"""
        print("Normalizing responses and linking with companies...")

        matched = 0
        unmatched = 0

        for response in self.responses:
            respondent_domain = self.extract_domain(response.email)

            # Try to match with company
            company = self.companies.get(respondent_domain)

            if company:
                account_domain = company.domain
                company_name = company.company
                region = company.region
                tenure_years = company.tenure_years
                matched += 1
            else:
                account_domain = ''
                company_name = ''
                region = ''
                tenure_years = ''
                if respondent_domain:
                    self.unmatched_domains.add(respondent_domain)
                    unmatched += 1

            # Create normalized response for each answer
            for question_short_form, answer_raw in response.answers.items():
                # Get question metadata
                question = self.questions.get(question_short_form)

                if not question:
                    self.unknown_questions.add(question_short_form)
                    question_group = 'Unknown'
                    original_question = question_short_form
                else:
                    question_group = question.question_group
                    original_question = question.original_question

                # Try to parse as numeric
                is_numeric = False
                answer_numeric = None
                try:
                    answer_numeric = float(answer_raw)
                    is_numeric = True
                    self.stats['numeric_answers'] += 1
                except ValueError:
                    self.stats['text_answers'] += 1

                normalized = NormalizedResponse(
                    year=response.year,
                    record_id=response.record_id,
                    email=response.email,
                    first_name=response.first_name,
                    last_name=response.last_name,
                    respondent_domain=respondent_domain,
                    account_domain=account_domain,
                    company_name=company_name,
                    region=region,
                    tenure_years=tenure_years,
                    survey_type=response.survey_type,
                    question_short_form=question_short_form,
                    question_group=question_group,
                    original_question=original_question,
                    answer_raw=answer_raw,
                    answer_numeric=answer_numeric,
                    is_numeric=is_numeric
                )

                self.normalized_responses.append(normalized)

        self.stats['matched_companies'] = matched
        self.stats['unmatched_domains'] = unmatched

        print(f"  ✓ Created {len(self.normalized_responses)} normalized records")
        print(f"  ✓ Matched {matched} responses to companies")
        print(f"  ✓ {unmatched} responses without company match\n")

    def calculate_stats(self, values: List[float]) -> Stats:
        """Calculate statistical measures for a list of values"""
        if not values:
            return Stats()

        return Stats(
            count=len(values),
            mean=statistics.mean(values),
            median=statistics.median(values),
            std_dev=statistics.stdev(values) if len(values) > 1 else 0.0,
            min_val=min(values),
            max_val=max(values)
        )

    def calculate_correlations(self) -> List[Dict]:
        """Calculate two types of correlations:
        1. Between answers for all questions and all respondents (current year)
        2. Between annual deltas for returning respondents
        """
        print("Calculating correlations...")

        correlations = []

        # Get all years
        all_years = sorted(set(r.year for r in self.normalized_responses))
        if len(all_years) < 2:
            print("  ⚠ Need at least 2 years of data for correlation analysis")
            return correlations

        prev_year = all_years[-2]
        curr_year = all_years[-1]

        # Get all numeric questions
        numeric_questions = sorted(set(
            r.question_short_form for r in self.normalized_responses if r.is_numeric
        ))

        # ============================================================
        # TYPE 1: Correlations between answers for all questions (current year)
        # ============================================================
        print(f"  Calculating correlations for current year ({curr_year}) responses...")

        # Build response matrix for current year
        current_year_matrix = defaultdict(dict)
        for resp in self.normalized_responses:
            if resp.year == curr_year and resp.is_numeric and resp.answer_numeric is not None:
                current_year_matrix[resp.email][resp.question_short_form] = resp.answer_numeric

        # Calculate pairwise correlations for current year
        for i, q1 in enumerate(numeric_questions):
            for q2 in numeric_questions[i+1:]:
                pairs = []
                for email, answers in current_year_matrix.items():
                    if q1 in answers and q2 in answers:
                        pairs.append((answers[q1], answers[q2]))

                if len(pairs) >= Thresholds.MIN_CORRELATION_PAIRS:
                    values1 = [p[0] for p in pairs]
                    values2 = [p[1] for p in pairs]

                    corr = self.pearson_correlation(values1, values2)

                    if corr is not None and abs(corr) >= Thresholds.STRONG_CORRELATION:
                        correlations.append({
                            'type': 'Current Year Responses',
                            'year': curr_year,
                            'question_1': q1,
                            'question_2': q2,
                            'correlation': round(corr, 3),
                            'n_pairs': len(pairs),
                            'interpretation': self.interpret_correlation(corr)
                        })

        # ============================================================
        # TYPE 2: Correlations between YoY deltas for returning respondents
        # ============================================================
        print(f"  Calculating correlations for YoY deltas...")

        # Identify returning respondents
        prev_emails = set(r.email for r in self.normalized_responses if r.year == prev_year)
        curr_emails = set(r.email for r in self.normalized_responses if r.year == curr_year)
        returning_emails = prev_emails & curr_emails

        # Build delta matrix for returning respondents
        delta_matrix = defaultdict(dict)  # email -> {question: delta}

        for email in returning_emails:
            for question in numeric_questions:
                # Get prev and curr values
                prev_val = None
                curr_val = None

                for resp in self.normalized_responses:
                    if resp.email == email and resp.question_short_form == question and resp.is_numeric:
                        if resp.year == prev_year:
                            prev_val = resp.answer_numeric
                        elif resp.year == curr_year:
                            curr_val = resp.answer_numeric

                # Calculate delta if both years have data
                if prev_val is not None and curr_val is not None:
                    delta_matrix[email][question] = curr_val - prev_val

        # Calculate pairwise correlations for deltas
        for i, q1 in enumerate(numeric_questions):
            for q2 in numeric_questions[i+1:]:
                pairs = []
                for email, deltas in delta_matrix.items():
                    if q1 in deltas and q2 in deltas:
                        pairs.append((deltas[q1], deltas[q2]))

                if len(pairs) >= Thresholds.MIN_CORRELATION_PAIRS:
                    values1 = [p[0] for p in pairs]
                    values2 = [p[1] for p in pairs]

                    corr = self.pearson_correlation(values1, values2)

                    if corr is not None and abs(corr) >= Thresholds.STRONG_CORRELATION:
                        correlations.append({
                            'type': 'YoY Delta',
                            'year': f'{prev_year}-{curr_year}',
                            'question_1': q1,
                            'question_2': q2,
                            'correlation': round(corr, 3),
                            'n_pairs': len(pairs),
                            'interpretation': self.interpret_correlation(corr)
                        })

        print(f"  ✓ Calculated {len(correlations)} correlations\n")
        return sorted(correlations, key=lambda x: (x['type'], abs(x['correlation'])), reverse=True)

    def pearson_correlation(self, x: List[float], y: List[float]) -> Optional[float]:
        """Calculate Pearson correlation coefficient"""
        if len(x) != len(y) or len(x) < 2:
            return None

        n = len(x)
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))

        std_x = statistics.stdev(x) if len(x) > 1 else 0
        std_y = statistics.stdev(y) if len(y) > 1 else 0

        if std_x == 0 or std_y == 0:
            return None

        denominator = std_x * std_y * n

        if denominator == 0:
            return None

        return numerator / denominator

    def interpret_correlation(self, corr: float) -> str:
        """Interpret correlation strength"""
        abs_corr = abs(corr)
        if abs_corr >= Thresholds.STRONG_CORRELATION:
            return 'Strong'
        elif abs_corr >= 0.4:
            return 'Moderate'
        elif abs_corr >= 0.2:
            return 'Weak'
        else:
            return 'Very Weak'

    def generate_outputs(self) -> None:
        """Generate correlation analysis output"""
        print("Generating output files...")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Calculate and write correlations
        correlations = self.calculate_correlations()
        self._write_correlations(correlations)

        print(f"\n✓ All output files generated in: {self.output_dir}\n")

    def _write_correlations(self, correlations: List[Dict]) -> None:
        """Write correlations.csv"""
        file_path = self.output_dir / 'correlations.csv'

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'type', 'year', 'question_1', 'question_2',
                'correlation', 'n_pairs', 'interpretation'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(correlations)

        print(f"  ✓ Wrote {file_path.name}")

    def print_summary(self) -> None:
        """Print analysis summary"""
        print("=" * 60)
        print("ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Total responses read:        {self.stats['rows_read']}")
        print(f"Matched to companies:        {self.stats['matched_companies']}")
        print(f"Unmatched domains:           {self.stats['unmatched_domains']}")
        print(f"Numeric answers:             {self.stats['numeric_answers']}")
        print(f"Text answers:                {self.stats['text_answers']}")
        print(f"Normalized records created:  {len(self.normalized_responses)}")
        print(f"Unknown questions found:     {len(self.unknown_questions)}")
        print("=" * 60)

    def run(self) -> None:
        """Execute the full analysis pipeline"""
        try:
            self.validate_structure()
            self.load_questions()
            self.load_companies()
            self.load_responses()
            self.normalize_responses()
            self.generate_outputs()
            self.print_summary()

            print("\n✓ Analysis completed successfully!")

        except Exception as e:
            print(f"\n✗ Error: {e}", file=sys.stderr)
            raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Customer Satisfaction Survey Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python survey_analyzer.py
  python survey_analyzer.py --input ./data/input --output ./data/output
        """
    )

    parser.add_argument(
        '--input',
        default='./input',
        help='Input directory path (default: ./input)'
    )

    parser.add_argument(
        '--output',
        default='./output',
        help='Output directory path (default: ./output)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Customer Satisfaction Survey Analysis Tool")
    print("=" * 60)
    print(f"Input directory:  {args.input}")
    print(f"Output directory: {args.output}")
    print("=" * 60)
    print()

    analyzer = SurveyAnalyzer(args.input, args.output)
    analyzer.run()


if __name__ == '__main__':
    main()
