"""
KAKEN Data Transformer

This module provides data transformation functionality to convert KAKEN JSON data
to Elasticsearch document format while preserving the original structure.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class KakenToElasticsearchTransformer:
    """Transform KAKEN JSON data to Elasticsearch document format"""

    def transform_researcher(self, kaken_data: Dict) -> Dict:
        """
        Transform KAKEN researcher data to Elasticsearch document format

        Args:
            kaken_data: Raw KAKEN JSON data

        Returns:
            Elasticsearch document ready for indexing
        """
        logger.debug(f"Transforming researcher data for: {kaken_data.get('accn', 'unknown')}")

        # Start with original data structure
        es_doc = kaken_data.copy()

        # Add search_text field for full-text search
        es_doc['search_text'] = self._build_search_text(kaken_data)

        # Ensure _source_url is present (should be set by ResourceSync client)
        if '_source_url' not in es_doc:
            logger.warning(f"No _source_url found for researcher: {kaken_data.get('accn', 'unknown')}")
            es_doc['_source_url'] = None

        logger.debug(f"Successfully transformed researcher data for: {es_doc.get('accn', 'unknown')}")
        return es_doc

    def _build_search_text(self, researcher_data: Dict) -> str:
        """
        Build combined search text from researcher data

        Args:
            researcher_data: NRID researcher data

        Returns:
            Combined search text string
        """
        search_parts = []

        # Extract name information
        name_parts = self._extract_name_text(researcher_data)
        search_parts.extend(name_parts)

        # Extract affiliation information
        affiliation_parts = self._extract_affiliation_text(researcher_data)
        search_parts.extend(affiliation_parts)

        # Extract project information
        project_parts = self._extract_project_text(researcher_data)
        search_parts.extend(project_parts)

        # Extract product information
        product_parts = self._extract_product_text(researcher_data)
        search_parts.extend(product_parts)

        # Filter out empty strings and join
        search_text = ' '.join(filter(None, search_parts))

        return search_text

    def _extract_name_text(self, data: Dict) -> List[str]:
        """Extract searchable text from name fields"""
        name_parts = []

        # Current name
        if 'name' in data:
            name_parts.extend(self._extract_human_readable_values(data['name']))

        # Name history
        if 'names' in data and isinstance(data['names'], list):
            for name_entry in data['names']:
                name_parts.extend(self._extract_human_readable_values(name_entry))

        return name_parts

    def _extract_affiliation_text(self, data: Dict) -> List[str]:
        """Extract searchable text from affiliation fields"""
        affiliation_parts = []

        if 'affiliations:history' in data and isinstance(data['affiliations:history'], list):
            for affiliation in data['affiliations:history']:
                # Institution name
                if 'affiliation:institution' in affiliation:
                    affiliation_parts.extend(
                        self._extract_human_readable_values(affiliation['affiliation:institution'])
                    )

                # Department name
                if 'affiliation:department' in affiliation:
                    affiliation_parts.extend(
                        self._extract_human_readable_values(affiliation['affiliation:department'])
                    )

                # Job title
                if 'affiliation:jobTitle' in affiliation:
                    affiliation_parts.extend(
                        self._extract_human_readable_values(affiliation['affiliation:jobTitle'])
                    )

        return affiliation_parts

    def _extract_project_text(self, data: Dict) -> List[str]:
        """Extract searchable text from project fields"""
        project_parts = []

        if 'work:project' in data and isinstance(data['work:project'], list):
            for project in data['work:project']:
                # Project title
                if 'title' in project:
                    project_parts.extend(self._extract_human_readable_values(project['title']))

                # Project category
                if 'category' in project:
                    project_parts.extend(self._extract_human_readable_values(project['category']))

                # Project field
                if 'field' in project:
                    project_parts.extend(self._extract_human_readable_values(project['field']))

                # Project keywords
                if 'keyword' in project:
                    project_parts.extend(self._extract_human_readable_values(project['keyword']))

                # Project institution
                if 'institution' in project:
                    project_parts.extend(self._extract_human_readable_values(project['institution']))

                # Project members
                if 'member' in project and isinstance(project['member'], list):
                    for member in project['member']:
                        if 'person:name' in member:
                            project_parts.extend(self._extract_human_readable_values(member['person:name']))
                        if 'institution:name' in member:
                            project_parts.extend(self._extract_human_readable_values(member['institution:name']))
                        if 'department:name' in member:
                            project_parts.extend(self._extract_human_readable_values(member['department:name']))
                        if 'jobTitle' in member:
                            project_parts.extend(self._extract_human_readable_values(member['jobTitle']))

        return project_parts

    def _extract_product_text(self, data: Dict) -> List[str]:
        """Extract searchable text from product fields"""
        product_parts = []

        if 'work:product' in data and isinstance(data['work:product'], list):
            for product in data['work:product']:
                # Product title
                if 'title:main' in product:
                    if isinstance(product['title:main'], dict) and 'text' in product['title:main']:
                        product_parts.append(product['title:main']['text'])

                # Product creators
                if 'creator:unparsed' in product:
                    product_parts.extend(self._extract_human_readable_values(product['creator:unparsed']))

                # Product contributors
                if 'contributor:organizer:unparsed' in product:
                    product_parts.extend(self._extract_human_readable_values(product['contributor:organizer:unparsed']))

                # Product creator candidates
                if 'attribute:creator:candidate' in product:
                    candidate_data = product['attribute:creator:candidate']
                    if isinstance(candidate_data, dict) and 'list' in candidate_data:
                        if isinstance(candidate_data['list'], list):
                            for candidate in candidate_data['list']:
                                if 'person:name' in candidate:
                                    product_parts.extend(self._extract_human_readable_values(candidate['person:name']))

        return product_parts

    def _extract_human_readable_values(self, data: Any) -> List[str]:
        """
        Extract human readable text values from nested data structures

        Args:
            data: Data structure that may contain humanReadableValue

        Returns:
            List of extracted text values
        """
        values = []

        if isinstance(data, dict):
            # Handle humanReadableValue structure
            if 'humanReadableValue' in data:
                hrv = data['humanReadableValue']
                if isinstance(hrv, list):
                    for item in hrv:
                        if isinstance(item, dict) and 'text' in item:
                            values.append(item['text'])
                elif isinstance(hrv, dict) and 'text' in hrv:
                    values.append(hrv['text'])

            # Handle direct text field
            if 'text' in data:
                values.append(data['text'])

        elif isinstance(data, list):
            # Handle list of objects
            for item in data:
                values.extend(self._extract_human_readable_values(item))

        return values

    def _normalize_date(self, date_obj: Dict) -> Optional[datetime]:
        """
        Normalize date object to datetime

        Args:
            date_obj: Date object from NRID data

        Returns:
            Normalized datetime object or None
        """
        if not isinstance(date_obj, dict):
            return None

        # Handle commonEra:year format
        if 'commonEra:year' in date_obj:
            year = date_obj['commonEra:year']
            month = date_obj.get('month', 1)
            day = date_obj.get('day', 1)

            try:
                # Handle string years
                if isinstance(year, str):
                    year = int(year)

                return datetime(year, month, day)
            except (ValueError, TypeError):
                logger.warning(f'Invalid date format: {date_obj}')
                return None

        # Handle fiscal:year format
        if 'fiscal:year' in date_obj:
            fiscal_year = date_obj['fiscal:year']
            if isinstance(fiscal_year, dict) and 'commonEra:year' in fiscal_year:
                year = fiscal_year['commonEra:year']
                month = fiscal_year.get('firstDate:month', 4)  # Default to April for fiscal year
                day = fiscal_year.get('firstDate:day', 1)

                try:
                    if isinstance(year, str):
                        year = int(year)

                    return datetime(year, month, day)
                except (ValueError, TypeError):
                    logger.warning(f'Invalid fiscal date format: {date_obj}')
                    return None

        return None
