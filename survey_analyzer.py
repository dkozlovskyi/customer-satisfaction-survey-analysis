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
            self.input_dir / 'meta',
            self.input_dir / 'responses' / 'previous',
            self.input_dir / 'responses' / 'current'
        ]

        for dir_path in required_dirs:
            if not dir_path.exists():
                raise FileNotFoundError(f"Required directory not found: {dir_path}")
            print(f"  ✓ Found: {dir_path}")

        # Check required files
        required_files = [
            self.input_dir / 'meta' / 'questions.csv',
            self.input_dir / 'meta' / 'companies.csv'
        ]

        for file_path in required_files:
            if not file_path.exists():
                raise FileNotFoundError(f"Required file not found: {file_path}")
            print(f"  ✓ Found: {file_path}")

        # Check for response files
        prev_files = list((self.input_dir / 'responses' / 'previous').glob('*.csv'))
        curr_files = list((self.input_dir / 'responses' / 'current').glob('*.csv'))

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
        file_path = self.input_dir / 'meta' / 'questions.csv'

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
        file_path = self.input_dir / 'meta' / 'companies.csv'

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
        prev_dir = self.input_dir / 'responses' / 'previous'
        for file_path in prev_dir.glob('*.csv'):
            year = self.extract_year_from_filename(file_path.name)
            self._load_response_file(file_path, year)

        # Load current year responses
        curr_dir = self.input_dir / 'responses' / 'current'
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

            # Identify question columns (exclude standard columns and non-analytical columns)
            standard_cols = {
                'Record ID', 'Email', 'Contact first name', 'Contact last name',
                'Date', 'Survey Type'
            }

            # Non-analytical columns to skip
            skip_cols = {
                'Survey ID',                          # Survey instance ID - no analytical value
                'Response',                           # NPS explanation - qualitative only
                'Sentiment',                          # Text representation of NPS - skip
                'Industry Standard Question Type',    # Question type metadata - skip
                'Source',                             # Survey distribution method - skip
                'Submission Name'                     # Submission title - skip
            }

            for row in reader:
                # Extract standard fields
                response = Response(
                    year=year,
                    record_id=row.get('Record ID', '').strip(),
                    email=row.get('Email', '').strip(),
                    first_name=row.get('Contact first name', '').strip(),
                    last_name=row.get('Contact last name', '').strip(),
                    date=row.get('Date', '').strip(),
                    survey_type=row.get('Survey Type', '').strip(),
                    answers={}
                )

                # Extract question answers (skip standard and non-analytical columns)
                for col, value in row.items():
                    if col not in standard_cols and col not in skip_cols and value.strip():
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

    def calculate_yoy_deltas(self) -> List[Dict]:
        """Calculate year-over-year deltas at respondent/question level"""
        print("Calculating year-over-year deltas...")

        # Group responses by email + question
        response_map = defaultdict(dict)  # (email, question) -> {year: answer_numeric}

        for resp in self.normalized_responses:
            if resp.is_numeric and resp.answer_numeric is not None:
                key = (resp.email, resp.question_short_form)
                response_map[key][resp.year] = resp.answer_numeric

        # Calculate deltas
        deltas = []
        years = sorted(set(r.year for r in self.normalized_responses))

        if len(years) >= 2:
            prev_year = years[0]
            curr_year = years[1]

            for (email, question), year_answers in response_map.items():
                if prev_year in year_answers and curr_year in year_answers:
                    prev_val = year_answers[prev_year]
                    curr_val = year_answers[curr_year]
                    delta = curr_val - prev_val

                    # Find corresponding normalized response for metadata
                    curr_resp = next(
                        (r for r in self.normalized_responses
                         if r.email == email and r.question_short_form == question and r.year == curr_year),
                        None
                    )

                    if curr_resp:
                        deltas.append({
                            'email': email,
                            'company_name': curr_resp.company_name,
                            'question_short_form': question,
                            'question_group': curr_resp.question_group,
                            'previous_year': prev_year,
                            'previous_value': prev_val,
                            'current_year': curr_year,
                            'current_value': curr_val,
                            'delta': delta,
                            'delta_pct': (delta / prev_val * 100) if prev_val != 0 else 0
                        })

        print(f"  ✓ Calculated {len(deltas)} year-over-year deltas\n")
        return deltas

    def aggregate_by_question(self) -> List[Dict]:
        """Aggregate responses by question with 2024/2025 comparison and significance detection"""
        print("Aggregating by question...")

        # Group by year and question
        groups = defaultdict(list)

        for resp in self.normalized_responses:
            if resp.is_numeric and resp.answer_numeric is not None:
                key = (resp.year, resp.question_short_form, resp.question_group)
                groups[key].append(resp.answer_numeric)

        # Calculate aggregates by question
        question_data = defaultdict(dict)  # question -> {year -> stats}

        for (year, question, group), values in groups.items():
            stats = self.calculate_stats(values)
            if question not in question_data:
                question_data[question] = {'group': group}
            question_data[question][year] = {
                'response_count': stats.count,
                'mean': round(stats.mean, 2),
                'median': round(stats.median, 2),
                'std_dev': round(stats.std_dev, 2)
            }

        # Get all years and sort them
        all_years = sorted(set(year for year, _, _ in groups.keys()))

        # Calculate deltas for each question group
        group_deltas = defaultdict(list)  # question_group -> [deltas]

        for question, data in question_data.items():
            if len(all_years) >= 2:
                prev_year = all_years[-2]
                curr_year = all_years[-1]
                if prev_year in data and curr_year in data:
                    delta = data[curr_year]['mean'] - data[prev_year]['mean']
                    group_deltas[data['group']].append(delta)

        # Calculate group delta statistics
        group_delta_stats = {}
        for group, deltas in group_deltas.items():
            if len(deltas) > 0:
                mean_delta = statistics.mean(deltas)
                std_delta = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
                group_delta_stats[group] = {
                    'mean_delta': mean_delta,
                    'std_delta': std_delta
                }

        # Build final aggregates (2025 rows only with 2024 data in columns)
        aggregates = []

        if len(all_years) >= 2:
            prev_year = all_years[-2]
            curr_year = all_years[-1]

            for question, data in question_data.items():
                if curr_year in data:  # Only include questions that have current year data
                    curr_data = data[curr_year]
                    question_group = data['group']

                    # Get previous year data if available
                    prev_data = data.get(prev_year, {
                        'response_count': 'N/A',
                        'mean': 'N/A',
                        'median': 'N/A',
                        'std_dev': 'N/A'
                    })

                    # Calculate delta
                    delta = 'N/A'
                    if prev_year in data:
                        delta = round(curr_data['mean'] - data[prev_year]['mean'], 2)

                    # Get group delta std dev
                    group_std_delta = 'N/A'
                    if question_group in group_delta_stats:
                        group_std_delta = round(group_delta_stats[question_group]['std_delta'], 2)

                    # Determine if change is significant
                    significant_change = 'no'
                    if isinstance(delta, (int, float)) and delta != 'N/A':
                        # Mark as significant if delta exceeds group std dev OR if absolute delta >= 0.5
                        if abs(delta) >= 0.5:
                            significant_change = 'yes'
                        elif question_group in group_delta_stats:
                            std_delta = group_delta_stats[question_group]['std_delta']
                            if 0 < std_delta < abs(delta):
                                significant_change = 'yes'

                    aggregates.append({
                        'year': curr_year,
                        'question_short_form': question,
                        'question_group': question_group,
                        '2024_response_count': prev_data['response_count'],
                        '2024_mean': prev_data['mean'],
                        '2024_median': prev_data['median'],
                        '2024_std_dev': prev_data['std_dev'],
                        '2025_response_count': curr_data['response_count'],
                        '2025_mean': curr_data['mean'],
                        '2025_median': curr_data['median'],
                        '2025_std_dev': curr_data['std_dev'],
                        '2025_delta': delta,
                        '2025_std_dev_group_deltas': group_std_delta,
                        'significant_change': significant_change
                    })

        print(f"  ✓ Created {len(aggregates)} question aggregates\n")
        return sorted(aggregates, key=lambda x: x['question_short_form'])

    def aggregate_by_question_group(self) -> List[Dict]:
        """Aggregate responses by question group with 2024/2025 comparison and significance detection"""
        print("Aggregating by question group...")

        # First, determine survey type for each question group from questions metadata
        group_to_survey_type = {}
        for question_short_form, question in self.questions.items():
            if question.question_group not in group_to_survey_type:
                group_to_survey_type[question.question_group] = question.survey_type

        # Group by year and question group
        groups = defaultdict(list)

        for resp in self.normalized_responses:
            if resp.is_numeric and resp.answer_numeric is not None:
                key = (resp.year, resp.question_group)
                groups[key].append(resp.answer_numeric)

        # Calculate aggregates by group
        group_data = defaultdict(dict)  # group -> {year -> stats}

        for (year, group), values in groups.items():
            stats = self.calculate_stats(values)
            if group not in group_data:
                group_data[group] = {'survey_type': group_to_survey_type.get(group, 'Unknown')}
            group_data[group][year] = {
                'response_count': stats.count,
                'mean': round(stats.mean, 2),
                'median': round(stats.median, 2),
                'std_dev': round(stats.std_dev, 2)
            }

        # Get all years and sort them
        all_years = sorted(set(year for year, _ in groups.keys()))

        # Calculate deltas for each survey type
        survey_type_deltas = defaultdict(list)  # survey_type -> [deltas]

        for group, data in group_data.items():
            if len(all_years) >= 2:
                prev_year = all_years[-2]
                curr_year = all_years[-1]
                if prev_year in data and curr_year in data:
                    delta = data[curr_year]['mean'] - data[prev_year]['mean']
                    survey_type = data['survey_type']
                    survey_type_deltas[survey_type].append(delta)

        # Calculate survey type delta statistics
        survey_type_delta_stats = {}
        for survey_type, deltas in survey_type_deltas.items():
            if len(deltas) > 0:
                std_delta = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
                survey_type_delta_stats[survey_type] = {
                    'std_delta': std_delta
                }

        # Build final aggregates (2025 rows only with 2024 data in columns)
        aggregates = []

        if len(all_years) >= 2:
            prev_year = all_years[-2]
            curr_year = all_years[-1]

            for group, data in group_data.items():
                if curr_year in data:  # Only include groups that have current year data
                    curr_data = data[curr_year]
                    survey_type = data['survey_type']

                    # Get previous year data if available
                    prev_data = data.get(prev_year, {
                        'response_count': 'N/A',
                        'mean': 'N/A',
                        'median': 'N/A',
                        'std_dev': 'N/A'
                    })

                    # Calculate delta
                    delta = 'N/A'
                    if prev_year in data:
                        delta = round(curr_data['mean'] - data[prev_year]['mean'], 2)

                    # Get survey type delta std dev
                    survey_type_std_delta = 'N/A'
                    if survey_type in survey_type_delta_stats:
                        survey_type_std_delta = round(survey_type_delta_stats[survey_type]['std_delta'], 2)

                    # Determine if change is significant (same logic as question_aggregates)
                    significant_change = 'no'
                    if isinstance(delta, (int, float)) and delta != 'N/A':
                        # Mark as significant if delta exceeds survey type std dev OR if absolute delta >= 0.5
                        if abs(delta) >= 0.5:
                            significant_change = 'yes'
                        elif survey_type in survey_type_delta_stats:
                            std_delta = survey_type_delta_stats[survey_type]['std_delta']
                            if abs(delta) > std_delta:
                                significant_change = 'yes'

                    aggregates.append({
                        'year': curr_year,
                        'question_group': group,
                        'survey_type': survey_type,
                        '2024_response_count': prev_data['response_count'],
                        '2024_mean': prev_data['mean'],
                        '2024_median': prev_data['median'],
                        '2024_std_dev': prev_data['std_dev'],
                        '2025_response_count': curr_data['response_count'],
                        '2025_mean': curr_data['mean'],
                        '2025_median': curr_data['median'],
                        '2025_std_dev': curr_data['std_dev'],
                        '2025_delta': delta,
                        '2025_std_dev_survey_type_deltas': survey_type_std_delta,
                        'significant_change': significant_change
                    })

        print(f"  ✓ Created {len(aggregates)} question group aggregates\n")
        return sorted(aggregates, key=lambda x: x['question_group'])

    def aggregate_by_segment(self) -> List[Dict]:
        """Aggregate responses by segment (region, tenure) and year"""
        print("Aggregating by segment...")

        aggregates = []

        # By Region
        groups = defaultdict(list)
        for resp in self.normalized_responses:
            if resp.is_numeric and resp.answer_numeric is not None and resp.region:
                key = (resp.year, 'Region', resp.region, resp.question_short_form)
                groups[key].append(resp.answer_numeric)

        for (year, segment_type, segment_value, question), values in groups.items():
            stats = self.calculate_stats(values)
            aggregates.append({
                'year': year,
                'segment_type': segment_type,
                'segment_value': segment_value,
                'question_short_form': question,
                'response_count': stats.count,
                'mean': round(stats.mean, 2),
                'median': round(stats.median, 2)
            })

        # By Survey Type
        groups = defaultdict(list)
        for resp in self.normalized_responses:
            if resp.is_numeric and resp.answer_numeric is not None:
                key = (resp.year, 'Survey Type', resp.survey_type, resp.question_short_form)
                groups[key].append(resp.answer_numeric)

        for (year, segment_type, segment_value, question), values in groups.items():
            stats = self.calculate_stats(values)
            aggregates.append({
                'year': year,
                'segment_type': segment_type,
                'segment_value': segment_value,
                'question_short_form': question,
                'response_count': stats.count,
                'mean': round(stats.mean, 2),
                'median': round(stats.median, 2)
            })

        print(f"  ✓ Created {len(aggregates)} segment aggregates\n")
        return sorted(aggregates, key=lambda x: (x['year'], x['segment_type'], x['segment_value']))

    def aggregate_by_account(self) -> List[Dict]:
        """Aggregate responses by account (company domain) showing all respondents"""
        print("Aggregating by account...")

        aggregates = []

        # Group by year, account_domain, and question
        for year in set(r.year for r in self.normalized_responses):
            # Get all accounts (companies)
            accounts = defaultdict(lambda: {'company_name': '', 'respondents': set(), 'responses': []})

            for resp in self.normalized_responses:
                if resp.year == year and resp.account_domain:
                    key = (resp.account_domain, resp.question_short_form)
                    accounts[key]['company_name'] = resp.company_name
                    accounts[key]['respondents'].add(f"{resp.first_name} {resp.last_name} ({resp.email})")
                    if resp.is_numeric and resp.answer_numeric is not None:
                        accounts[key]['responses'].append(resp.answer_numeric)

            # Calculate aggregates for each account/question combination
            for (domain, question), data in accounts.items():
                if data['responses']:  # Only if we have numeric responses
                    stats = self.calculate_stats(data['responses'])
                    aggregates.append({
                        'year': year,
                        'account_domain': domain,
                        'company_name': data['company_name'],
                        'question_short_form': question,
                        'respondent_count': len(data['respondents']),
                        'respondents': '; '.join(sorted(data['respondents'])),
                        'response_count': stats.count,
                        'mean': round(stats.mean, 2),
                        'median': round(stats.median, 2),
                        'min': stats.min_val,
                        'max': stats.max_val
                    })

        print(f"  ✓ Created {len(aggregates)} account aggregates\n")
        return sorted(aggregates, key=lambda x: (x['year'], x['company_name'], x['question_short_form']))

    def calculate_correlations(self) -> List[Dict]:
        """Calculate correlations between numeric questions for latest year only"""
        print("Calculating correlations...")

        correlations = []

        # Get all numeric questions
        numeric_questions = set(
            r.question_short_form for r in self.normalized_responses if r.is_numeric
        )

        # Get latest year only
        years = set(r.year for r in self.normalized_responses)
        if not years:
            return correlations

        latest_year = max(years)
        print(f"  Calculating correlations for latest year: {latest_year}")

        # Overall correlations (no segmentation)
        response_matrix = defaultdict(dict)
        for resp in self.normalized_responses:
            if resp.year == latest_year and resp.is_numeric and resp.answer_numeric is not None:
                response_matrix[resp.email][resp.question_short_form] = resp.answer_numeric

        correlations.extend(self._calculate_correlations_for_segment(
            response_matrix, numeric_questions, latest_year, 'Overall', 'All'
        ))

        # Region-based correlations (US, Canada, Rest of the World)
        region_segments = {
            'US': 'US',
            'Canada': 'Canada',
            'Rest of the World': ['Europe', 'Asia Pacific', 'Latin America', 'Other']
        }

        for segment_name, region_filter in region_segments.items():
            response_matrix_region = defaultdict(dict)

            for resp in self.normalized_responses:
                if resp.year == latest_year and resp.is_numeric and resp.answer_numeric is not None:
                    # Check if region matches
                    if isinstance(region_filter, str):
                        if resp.region == region_filter:
                            response_matrix_region[resp.email][resp.question_short_form] = resp.answer_numeric
                    else:  # List of regions for "Rest of the World"
                        if resp.region in region_filter or (resp.region and resp.region not in ['US', 'Canada']):
                            response_matrix_region[resp.email][resp.question_short_form] = resp.answer_numeric

            if response_matrix_region:
                correlations.extend(self._calculate_correlations_for_segment(
                    response_matrix_region, numeric_questions, latest_year, 'Region', segment_name
                ))

        # Tenure-based correlations (>4 years vs <4 years)
        tenure_segments = {
            '>4 years': lambda t: self._parse_tenure(t) > 4,
            '≤4 years': lambda t: 0 < self._parse_tenure(t) <= 4
        }

        for segment_name, tenure_filter in tenure_segments.items():
            response_matrix_tenure = defaultdict(dict)

            for resp in self.normalized_responses:
                if resp.year == latest_year and resp.is_numeric and resp.answer_numeric is not None:
                    if tenure_filter(resp.tenure_years):
                        response_matrix_tenure[resp.email][resp.question_short_form] = resp.answer_numeric

            if response_matrix_tenure:
                correlations.extend(self._calculate_correlations_for_segment(
                    response_matrix_tenure, numeric_questions, latest_year, 'Tenure', segment_name
                ))

        print(f"  ✓ Calculated {len(correlations)} correlations\n")
        return sorted(correlations, key=lambda x: (x['segment_type'], x['segment_value'], abs(x['correlation'])), reverse=True)

    def _parse_tenure(self, tenure_str: str) -> float:
        """Parse tenure string to float"""
        if not tenure_str:
            return 0.0
        try:
            return float(tenure_str)
        except ValueError:
            return 0.0

    def _calculate_correlations_for_segment(
        self,
        response_matrix: Dict,
        numeric_questions: Set[str],
        year: int,
        segment_type: str,
        segment_value: str
    ) -> List[Dict]:
        """Calculate pairwise correlations for a given segment"""
        correlations = []
        question_list = sorted(numeric_questions)

        for i, q1 in enumerate(question_list):
            for q2 in question_list[i+1:]:
                # Get paired values
                pairs = []
                for email, answers in response_matrix.items():
                    if q1 in answers and q2 in answers:
                        pairs.append((answers[q1], answers[q2]))

                if len(pairs) >= 3:  # Need at least 3 pairs for meaningful correlation
                    values1 = [p[0] for p in pairs]
                    values2 = [p[1] for p in pairs]

                    # Calculate Pearson correlation
                    corr = self.pearson_correlation(values1, values2)

                    # Only include Strong correlations (|r| >= 0.7)
                    if corr is not None and abs(corr) >= 0.7:
                        correlations.append({
                            'year': year,
                            'segment_type': segment_type,
                            'segment_value': segment_value,
                            'question_1': q1,
                            'question_2': q2,
                            'correlation': round(corr, 3),
                            'n_pairs': len(pairs),
                            'interpretation': 'Strong'
                        })

        return correlations

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
        if abs_corr >= 0.7:
            return 'Strong'
        elif abs_corr >= 0.4:
            return 'Moderate'
        elif abs_corr >= 0.2:
            return 'Weak'
        else:
            return 'Very Weak'

    def sanitize_filename(self, company_name: str) -> str:
        """Sanitize company name for use as filename"""
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^\w\s-]', '', company_name)
        sanitized = re.sub(r'[\s]+', '_', sanitized)
        return sanitized.strip('_')

    def generate_account_reports(self) -> None:
        """Generate one CSV file per customer account with individual analysis"""
        print("Generating per-account reports...")

        # Get all years
        all_years = sorted(set(r.year for r in self.normalized_responses))
        if len(all_years) < 2:
            print("  ⚠ Need at least 2 years of data for account reports")
            return

        prev_year = all_years[-2]
        curr_year = all_years[-1]

        # Create accounts subdirectory
        accounts_dir = self.output_dir / 'accounts'
        accounts_dir.mkdir(parents=True, exist_ok=True)

        # Group responses by company
        company_responses = defaultdict(list)
        for resp in self.normalized_responses:
            if resp.company_name:  # Only include responses with matched companies
                company_responses[resp.company_name].append(resp)

        # Generate a report for each company
        for company_name, responses in sorted(company_responses.items()):
            self._write_account_report(company_name, responses, prev_year, curr_year, accounts_dir)

        print(f"  ✓ Generated {len(company_responses)} account reports in accounts/\n")

    def _write_account_report(self, company_name: str, responses: List[NormalizedResponse],
                              prev_year: int, curr_year: int, accounts_dir: Path) -> None:
        """Write a single account report CSV file"""
        filename = self.sanitize_filename(company_name) + '.csv'
        file_path = accounts_dir / filename

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Top-level: Responses table
            self._write_responses_section(writer, responses, prev_year, curr_year)

            # Add blank row between sections
            writer.writerow([])

            # Section 1: YoY Changes
            self._write_yoy_changes_section(writer, responses, prev_year, curr_year)

            # Add blank row between sections
            writer.writerow([])

            # Section 2: NPS Status and Transitions
            self._write_nps_section(writer, responses, prev_year, curr_year)

            # Add blank row between sections
            writer.writerow([])

            # Section 3: CSAT Status
            self._write_csat_section(writer, responses, curr_year)

            # Add blank row between sections
            writer.writerow([])

            # Section 4: Open Answers
            self._write_open_answers_section(writer, responses, curr_year)

        print(f"  ✓ Wrote accounts/{filename}")

    def _write_responses_section(self, writer, responses: List[NormalizedResponse],
                                 prev_year: int, curr_year: int) -> None:
        """Write RESPONSES section showing all responses for all respondents"""
        writer.writerow(['### SECTION 1: All Account Responses ###'])

        # Collect all questions across all respondents
        all_questions = set()
        respondent_data = {}

        for resp in responses:
            if resp.is_numeric and resp.year == curr_year:
                # Store respondent info and answers
                if resp.email not in respondent_data:
                    respondent_data[resp.email] = {
                        'first_name': resp.first_name,
                        'last_name': resp.last_name,
                        'answers': {}
                    }

                respondent_data[resp.email]['answers'][resp.question_short_form] = resp.answer_numeric
                all_questions.add(resp.question_short_form)

        if not respondent_data:
            writer.writerow(['No responses found'])
            return

        # Sort questions for consistent column order
        sorted_questions = sorted(all_questions)

        # Write header
        header = ['Email', 'First Name', 'Last Name'] + sorted_questions
        writer.writerow(header)

        # Write data rows
        for email in sorted(respondent_data.keys()):
            data = respondent_data[email]
            row = [
                email,
                data['first_name'],
                data['last_name']
            ]

            # Add answer for each question (or empty if not answered)
            for question in sorted_questions:
                row.append(data['answers'].get(question, ''))

            writer.writerow(row)

    def _write_new_submissions_section(self, writer, responses: List[NormalizedResponse],
                                       prev_year: int, curr_year: int) -> None:
        """Write New Submissions section with questions as columns"""
        writer.writerow(['### SECTION 1: NEW SUBMISSIONS ###'])
        writer.writerow(['First-time respondents (not in previous year)'])
        writer.writerow([])

        # Identify emails in each year
        prev_emails = set(r.email for r in responses if r.year == prev_year)
        curr_emails = set(r.email for r in responses if r.year == curr_year)
        new_emails = curr_emails - prev_emails

        if not new_emails:
            writer.writerow(['No new submissions found'])
            return

        # Collect all questions across all new respondents
        all_questions = set()
        respondent_data = {}

        for email in new_emails:
            # Get all numeric responses for this person
            person_responses = [r for r in responses
                              if r.email == email and r.year == curr_year and r.is_numeric]

            if not person_responses:
                continue

            # Calculate individual baseline (std dev of their answers)
            numeric_values = [r.answer_numeric for r in person_responses]
            individual_baseline = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0.0
            mean_value = statistics.mean(numeric_values) if numeric_values else 0.0

            # Store respondent info and answers
            answer_map = {r.question_short_form: r.answer_numeric for r in person_responses}
            all_questions.update(answer_map.keys())

            # Count low scores (<8)
            low_score_count = sum(1 for v in numeric_values if v < 8)

            respondent_data[email] = {
                'first_name': person_responses[0].first_name,
                'last_name': person_responses[0].last_name,
                'baseline': individual_baseline,
                'mean': mean_value,
                'answers': answer_map,
                'low_score_count': low_score_count,
                'lowest_score': min(numeric_values),
                'highest_score': max(numeric_values)
            }

        if not respondent_data:
            writer.writerow(['No new submissions with numeric responses found'])
            return

        # Sort questions for consistent column order
        sorted_questions = sorted(all_questions)

        # Write header
        header = ['Email', 'First Name', 'Last Name', 'Individual Baseline (Std Dev)',
                 'Lowest Score', 'Highest Score', 'Count Scores <8'] + sorted_questions
        writer.writerow(header)

        # Write data rows
        for email in sorted(respondent_data.keys()):
            data = respondent_data[email]
            row = [
                email,
                data['first_name'],
                data['last_name'],
                round(data['baseline'], 2),
                data['lowest_score'],
                data['highest_score'],
                data['low_score_count']
            ]

            # Add answer for each question (or empty if not answered)
            for question in sorted_questions:
                row.append(data['answers'].get(question, ''))

            writer.writerow(row)

    def _write_yoy_changes_section(self, writer, responses: List[NormalizedResponse],
                                   prev_year: int, curr_year: int) -> None:
        """Write YoY Changes section - only showing significant changes"""
        writer.writerow(['### SECTION 2: Significant YoY Changes ###'])

        # Identify returning respondents
        prev_emails = set(r.email for r in responses if r.year == prev_year)
        curr_emails = set(r.email for r in responses if r.year == curr_year)
        returning_emails = prev_emails & curr_emails

        if not returning_emails:
            writer.writerow(['No returning respondents found'])
            return

        # Build response map: (email, question) -> {year: value}
        response_map = defaultdict(dict)
        for resp in responses:
            if resp.is_numeric and resp.email in returning_emails:
                key = (resp.email, resp.question_short_form, resp.question_group)
                response_map[key][resp.year] = resp.answer_numeric

        # Calculate deltas grouped by question group
        deltas_by_group = defaultdict(list)
        delta_records = []

        for (email, question, group), year_values in response_map.items():
            if prev_year in year_values and curr_year in year_values:
                delta = year_values[curr_year] - year_values[prev_year]
                deltas_by_group[group].append(delta)

                # Get respondent info
                resp_info = next((r for r in responses if r.email == email and r.year == curr_year), None)
                if resp_info:
                    delta_records.append({
                        'email': email,
                        'first_name': resp_info.first_name,
                        'last_name': resp_info.last_name,
                        'question': question,
                        'group': group,
                        'prev_value': year_values[prev_year],
                        'curr_value': year_values[curr_year],
                        'delta': delta
                    })

        # Calculate baseline (std dev) for each question group
        group_baselines = {}
        for group, deltas in deltas_by_group.items():
            if len(deltas) > 1:
                group_baselines[group] = statistics.stdev(deltas)
            else:
                group_baselines[group] = 0.0

        # Filter records to only include significant changes
        significant_records = []
        for record in delta_records:
            group_baseline = group_baselines.get(record['group'], 0.0)
            strong_deviation = group_baseline > 0 and abs(record['delta']) > group_baseline
            large_change = abs(record['delta']) > 1

            # Only include if either condition is true
            if strong_deviation or large_change:
                record['group_baseline'] = group_baseline
                record['strong_deviation'] = 'yes' if strong_deviation else 'no'
                record['large_change'] = 'yes' if large_change else 'no'
                significant_records.append(record)

        if not significant_records:
            writer.writerow(['No significant changes found'])
            return

        # Header
        writer.writerow(['Email', 'First Name', 'Last Name', 'Question Group', 'Question',
                        f'{prev_year} Value', f'{curr_year} Value', 'Delta',
                        'Group Baseline (Std Dev)', 'Strong Deviation (>baseline)',
                        'Large Absolute Change (>1)'])

        # Write significant delta records sorted by group and email
        for record in sorted(significant_records, key=lambda x: (x['group'], x['email'], x['question'])):
            writer.writerow([
                record['email'],
                record['first_name'],
                record['last_name'],
                record['group'],
                record['question'],
                record['prev_value'],
                record['curr_value'],
                round(record['delta'], 2),
                round(record['group_baseline'], 2),
                record['strong_deviation'],
                record['large_change']
            ])

    def _write_nps_section(self, writer, responses: List[NormalizedResponse],
                          prev_year: int, curr_year: int) -> None:
        """Write NPS Status and Transitions section"""
        writer.writerow(['### SECTION 3: NPS Status & YoY Transitions ###'])

        # Find NPS question - use "Rating" label
        nps_question = 'Rating'

        # Check if this question exists in our questions metadata
        if nps_question not in self.questions:
            writer.writerow(['No NPS question (Rating) found in metadata'])
            return

        # Get NPS responses
        nps_responses = [r for r in responses if r.question_short_form == nps_question and r.is_numeric]

        if not nps_responses:
            writer.writerow(['No NPS responses found'])
            return

        # Build NPS map: email -> {year: (score, status)}
        nps_map = defaultdict(dict)

        def get_nps_status(score):
            if score >= 9:
                return 'Promoter'
            elif score >= 7:
                return 'Passive'
            else:
                return 'Detractor'

        for resp in nps_responses:
            status = get_nps_status(resp.answer_numeric)
            nps_map[resp.email][resp.year] = (resp.answer_numeric, status)

        # Header
        writer.writerow(['Email', 'First Name', 'Last Name',
                        f'{prev_year} NPS Score', f'{prev_year} Status',
                        f'{curr_year} NPS Score', f'{curr_year} Status',
                        'Status Change', 'Category Transition'])

        # Write NPS data - ordered by email
        for email in sorted(nps_map.keys()):
            # Get respondent info from current year
            resp_info = next((r for r in responses if r.email == email and r.year == curr_year), None)
            if not resp_info:
                continue

            prev_data = nps_map[email].get(prev_year, (None, None))
            curr_data = nps_map[email].get(curr_year, (None, None))

            prev_score, prev_status = prev_data
            curr_score, curr_status = curr_data

            # Determine if status changed
            if prev_status and curr_status:
                status_change = 'yes' if prev_status != curr_status else 'no'
                category_transition = f'{prev_status} → {curr_status}' if prev_status != curr_status else 'No change'
            else:
                status_change = 'N/A'
                category_transition = 'N/A'

            writer.writerow([
                email,
                resp_info.first_name,
                resp_info.last_name,
                prev_score if prev_score is not None else 'N/A',
                prev_status if prev_status else 'N/A',
                curr_score if curr_score is not None else 'N/A',
                curr_status if curr_status else 'N/A',
                status_change,
                category_transition
            ])

    def _write_csat_section(self, writer, responses: List[NormalizedResponse],
                           curr_year: int) -> None:
        """Write CSAT Status section"""
        writer.writerow(['### SECTION 4: CSAT Status & Transitions ###'])

        # Use "Customer Satisfaction Rating" label
        csat_question = 'Customer Satisfaction Rating'

        # Check if this question exists in our questions metadata
        if csat_question not in self.questions:
            writer.writerow(['No CSAT question (Customer Satisfaction Rating) found in metadata'])
            return

        # Get current year CSAT responses
        csat_responses = [r for r in responses
                         if r.question_short_form == csat_question
                         and r.year == curr_year
                         and r.is_numeric]

        if not csat_responses:
            writer.writerow(['No CSAT responses found for current year'])
            return

        # Header
        writer.writerow(['Email', 'First Name', 'Last Name', 'CSAT Score'])

        # Write CSAT data - ordered by email
        for resp in sorted(csat_responses, key=lambda x: x.email):
            writer.writerow([
                resp.email,
                resp.first_name,
                resp.last_name,
                resp.answer_numeric
            ])

    def _write_open_answers_section(self, writer, responses: List[NormalizedResponse],
                                    curr_year: int) -> None:
        """Write Open Answers section"""
        writer.writerow(['### SECTION 5: Open-ended Text Responses ###'])

        # Get all text (non-numeric) responses for current year
        text_responses = defaultdict(lambda: defaultdict(str))

        for resp in responses:
            if resp.year == curr_year and not resp.is_numeric:
                text_responses[resp.email][resp.question_short_form] = resp.answer_raw

        if not text_responses:
            writer.writerow(['No open-ended responses found'])
            return

        # Identify available open-ended question columns
        all_text_questions = set()
        for email_responses in text_responses.values():
            all_text_questions.update(email_responses.keys())

        # Header - Email, First Name, Last Name, then all text question columns
        header = ['Email', 'First Name', 'Last Name'] + sorted(all_text_questions)
        writer.writerow(header)

        # Write open answer data
        for email in sorted(text_responses.keys()):
            # Get respondent info
            resp_info = next((r for r in responses if r.email == email and r.year == curr_year), None)
            if not resp_info:
                continue

            row = [email, resp_info.first_name, resp_info.last_name]

            # Add each text question's answer
            for question in sorted(all_text_questions):
                row.append(text_responses[email].get(question, ''))

            writer.writerow(row)

    def generate_outputs(self) -> None:
        """Generate all output CSV files"""
        print("Generating output files...")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Normalized responses
        self._write_normalized_responses()

        # 2. Question aggregates
        question_aggs = self.aggregate_by_question()
        self._write_question_aggregates(question_aggs)

        # 3. Question group aggregates
        group_aggs = self.aggregate_by_question_group()
        self._write_question_group_aggregates(group_aggs)

        # 4. Correlations
        correlations = self.calculate_correlations()
        self._write_correlations(correlations)

        # 5. Per-account reports with individual analysis
        self.generate_account_reports()

        # 6. Unmatched domains (only if there are unmatched domains)
        if self.unmatched_domains:
            self._write_unmatched_domains()

        # 7. Unknown questions (only if there are unknown questions)
        if self.unknown_questions:
            self._write_unknown_questions()

        print(f"\n✓ All output files generated in: {self.output_dir}\n")

    def _write_normalized_responses(self) -> None:
        """Write normalized_responses.csv"""
        file_path = self.output_dir / 'normalized_responses.csv'

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'year', 'record_id', 'email', 'first_name', 'last_name',
                'respondent_domain', 'account_domain', 'company_name', 'region',
                'tenure_years', 'survey_type', 'question_short_form', 'question_group',
                'original_question', 'answer_raw', 'answer_numeric', 'is_numeric'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for resp in self.normalized_responses:
                writer.writerow({
                    'year': resp.year,
                    'record_id': resp.record_id,
                    'email': resp.email,
                    'first_name': resp.first_name,
                    'last_name': resp.last_name,
                    'respondent_domain': resp.respondent_domain,
                    'account_domain': resp.account_domain,
                    'company_name': resp.company_name,
                    'region': resp.region,
                    'tenure_years': resp.tenure_years,
                    'survey_type': resp.survey_type,
                    'question_short_form': resp.question_short_form,
                    'question_group': resp.question_group,
                    'original_question': resp.original_question,
                    'answer_raw': resp.answer_raw,
                    'answer_numeric': resp.answer_numeric if resp.is_numeric else '',
                    'is_numeric': resp.is_numeric
                })

        print(f"  ✓ Wrote {file_path.name}")

    def _write_yoy_deltas(self, deltas: List[Dict]) -> None:
        """Write yoy_deltas.csv"""
        file_path = self.output_dir / 'yoy_deltas.csv'

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'email', 'company_name', 'question_short_form', 'question_group',
                'previous_year', 'previous_value', 'current_year', 'current_value',
                'delta', 'delta_pct'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(deltas)

        print(f"  ✓ Wrote {file_path.name}")

    def _write_question_aggregates(self, aggregates: List[Dict]) -> None:
        """Write question_aggregates.csv"""
        file_path = self.output_dir / 'question_aggregates.csv'

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'year', 'question_short_form', 'question_group',
                '2024_response_count', '2024_mean', '2024_median', '2024_std_dev',
                '2025_response_count', '2025_mean', '2025_median', '2025_std_dev',
                '2025_delta', '2025_std_dev_group_deltas', 'significant_change'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(aggregates)

        print(f"  ✓ Wrote {file_path.name}")

    def _write_question_group_aggregates(self, aggregates: List[Dict]) -> None:
        """Write question_group_aggregates.csv"""
        file_path = self.output_dir / 'question_group_aggregates.csv'

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'year', 'question_group', 'survey_type',
                '2024_response_count', '2024_mean', '2024_median', '2024_std_dev',
                '2025_response_count', '2025_mean', '2025_median', '2025_std_dev',
                '2025_delta', '2025_std_dev_survey_type_deltas', 'significant_change'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(aggregates)

        print(f"  ✓ Wrote {file_path.name}")

    def _write_segment_aggregates(self, aggregates: List[Dict]) -> None:
        """Write segment_aggregates.csv"""
        file_path = self.output_dir / 'segment_aggregates.csv'

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'year', 'segment_type', 'segment_value', 'question_short_form',
                'response_count', 'mean', 'median'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(aggregates)

        print(f"  ✓ Wrote {file_path.name}")

    def _write_account_aggregates(self, aggregates: List[Dict]) -> None:
        """Write account_aggregates.csv"""
        file_path = self.output_dir / 'account_aggregates.csv'

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'year', 'account_domain', 'company_name', 'question_short_form',
                'respondent_count', 'respondents', 'response_count', 'mean', 'median', 'min', 'max'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(aggregates)

        print(f"  ✓ Wrote {file_path.name}")

    def _write_correlations(self, correlations: List[Dict]) -> None:
        """Write correlations.csv"""
        file_path = self.output_dir / 'correlations.csv'

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'year', 'segment_type', 'segment_value', 'question_1', 'question_2',
                'correlation', 'n_pairs', 'interpretation'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(correlations)

        print(f"  ✓ Wrote {file_path.name}")

    def _write_unmatched_domains(self) -> None:
        """Write unmatched_domains.csv with full customer details"""
        file_path = self.output_dir / 'unmatched_domains.csv'

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['email', 'first_name', 'last_name', 'domain', 'response_count']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            # Collect unique customers with unmatched domains
            unmatched_customers = defaultdict(lambda: {'email': '', 'first_name': '', 'last_name': '', 'domain': '', 'count': 0})

            for resp in self.normalized_responses:
                if resp.respondent_domain in self.unmatched_domains:
                    key = resp.email
                    if not unmatched_customers[key]['email']:
                        unmatched_customers[key]['email'] = resp.email
                        unmatched_customers[key]['first_name'] = resp.first_name
                        unmatched_customers[key]['last_name'] = resp.last_name
                        unmatched_customers[key]['domain'] = resp.respondent_domain
                    unmatched_customers[key]['count'] += 1

            # Write sorted by email
            for customer in sorted(unmatched_customers.values(), key=lambda x: x['email']):
                writer.writerow({
                    'email': customer['email'],
                    'first_name': customer['first_name'],
                    'last_name': customer['last_name'],
                    'domain': customer['domain'],
                    'response_count': customer['count']
                })

        print(f"  ✓ Wrote {file_path.name}")

    def _write_unknown_questions(self) -> None:
        """Write unknown_questions.csv"""
        file_path = self.output_dir / 'unknown_questions.csv'

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['question_column', 'occurrences'])

            # Count occurrences
            question_counts = defaultdict(int)
            for resp in self.normalized_responses:
                if resp.question_short_form in self.unknown_questions:
                    question_counts[resp.question_short_form] += 1

            for question in sorted(self.unknown_questions):
                writer.writerow([question, question_counts[question]])

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
