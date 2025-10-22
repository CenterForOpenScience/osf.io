"""
ResourceSync Client for KAKEN

This module provides ResourceSync client functionality to synchronize
researcher data from KAKEN database via NRID (National Research ID) system.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Iterator, Tuple
from urllib.parse import urljoin, urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dateutil.parser import parse as parse_datetime

import logging
logger = logging.getLogger(__name__)


class ResourceSyncClient:
    """ResourceSync client for KAKEN data via NRID system"""

    def __init__(self,
                 resourcesync_url: str,
                 timeout: int = 60,
                 max_retries: int = 3):
        """
        Initialize ResourceSync client

        Args:
            resourcesync_url: ResourceSync discovery URL (required)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        if not resourcesync_url:
            raise ValueError('resourcesync_url is required')

        self.resourcesync_url = resourcesync_url
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        # Base URL for resolving relative URLs
        self.base_url = self._extract_base_url(self.resourcesync_url)

    def _extract_base_url(self, url: str) -> str:
        """Extract base URL from ResourceSync URL"""
        parsed = urlparse(url)
        return f'{parsed.scheme}://{parsed.netloc}'

    def _fetch_xml(self, url: str) -> ET.Element:
        """
        Fetch and parse XML from URL

        Args:
            url: URL to fetch

        Returns:
            Parsed XML root element

        Raises:
            requests.RequestException: If request fails
            ET.ParseError: If XML parsing fails
        """
        logger.info(f'Fetching XML from: {url}')

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse XML safely
            root = ET.fromstring(response.content)
            logger.debug(f'Successfully parsed XML from {url}')
            return root

        except requests.RequestException as e:
            logger.exception(f'Failed to fetch XML from {url}: {e}')
            raise
        except ET.ParseError as e:
            logger.exception(f'Failed to parse XML from {url}: {e}')
            raise

    def get_capability_list(self) -> Dict:
        """
        Get capability list from ResourceSync discovery endpoint

        Returns:
            Dictionary containing capability list information
        """
        logger.info('Fetching capability list')

        # Fetch ResourceSync discovery document
        root = self._fetch_xml(self.resourcesync_url)

        # Find capability list URL in sitemap
        capability_url = None

        # ResourceSync discovery uses sitemap format
        # Look for URL with capability metadata
        for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
            loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc_elem is not None:
                # Check for capability metadata
                metadata = url_elem.find('.//{http://www.openarchives.org/rs/terms/}md')
                if metadata is not None and metadata.get('capability') == 'capabilitylist':
                    capability_url = loc_elem.text
                    break

        if not capability_url:
            # Log the XML structure for debugging
            logger.debug(f'XML root tag: {root.tag}')
            logger.debug(f'XML namespaces: {root.attrib}')
            for elem in root.iter():
                logger.debug(f'Element: {elem.tag}, attrib: {elem.attrib}, text: {elem.text}')
            raise ValueError('Capability list URL not found in ResourceSync discovery')

        # Resolve relative URL
        capability_url = urljoin(self.base_url, capability_url)

        # Fetch capability list
        cap_root = self._fetch_xml(capability_url)

        # Parse capability list
        capabilities = {
            'url': capability_url,
            'modified': None,
            'resourcelists': [],
            'changelists': []
        }

        # Extract modified time from urlset
        if 'modified' in cap_root.attrib:
            capabilities['modified'] = cap_root.attrib['modified']

        # Extract resource lists and change lists
        for url_elem in cap_root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
            loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            lastmod = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
            if loc is not None:
                url = loc.text
                lastmod_dt = None
                if lastmod is not None:
                    try:
                        lastmod_dt = parse_datetime(lastmod.text)
                    except ValueError:
                        logger.warning(f'Invalid lastmod format: {lastmod.text}')

                # Check metadata for capability type
                metadata = url_elem.find('.//{http://www.openarchives.org/rs/terms/}md')
                if metadata is not None:
                    capability = metadata.get('capability')
                    if capability == 'resourcelist':
                        capabilities['resourcelists'].append({'url': url, 'lastmod': lastmod_dt})
                    elif capability == 'changelist':
                        capabilities['changelists'].append({'url': url, 'lastmod': lastmod_dt})

        logger.info(f"Found {len(capabilities['resourcelists'])} resource lists and {len(capabilities['changelists'])} change lists")
        return capabilities

    def get_resource_lists(self) -> List[str]:
        """
        Get list of resource list URLs

        Returns:
            List of resource list URLs
        """
        capabilities = self.get_capability_list()
        return [item['url'] for item in capabilities['resourcelists']]

    def get_change_lists(self) -> List[str]:
        """
        Get list of change list URLs

        Returns:
            List of change list URLs
        """
        capabilities = self.get_capability_list()
        return [item['url'] for item in capabilities['changelists']]

    def process_resource_list(self, url: str) -> Iterator[Tuple[str, datetime]]:
        """
        Process a resource list and yield individual JSON URLs

        Args:
            url: Resource list URL

        Yields:
            Individual researcher JSON URLs
        """
        logger.info(f'Processing resource list: {url}')

        root = self._fetch_xml(url)

        # Extract JSON URLs from sitemap
        json_urls: List[Tuple[str, datetime]] = []
        for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
            loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            lastmod = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
            if loc is not None and loc.text.endswith('.json'):
                if lastmod is None or not lastmod.text:
                    raise ValueError('Missing per-item lastmod in resource list')
                try:
                    lastmod_dt = parse_datetime(lastmod.text)
                except ValueError:
                    raise
                json_urls.append((loc.text, lastmod_dt))

        logger.info(f'Found {len(json_urls)} JSON URLs in resource list')

        for json_url, lastmod_dt in json_urls:
            yield (json_url, lastmod_dt)

    def process_change_list(self, url: str) -> Iterator[Tuple[str, str, datetime]]:
        """
        Process a change list and yield changes since specified time

        Args:
            url: Change list URL

        Yields:
            Tuple of (action, json_url, lastmod_datetime)
            where action is 'created', 'updated', or 'deleted'
        """
        logger.info(f'Processing change list: {url}')

        root = self._fetch_xml(url)

        changes = []
        for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
            loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            lastmod = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')

            if loc is not None and loc.text and loc.text.endswith('.json'):
                if lastmod is None or not lastmod.text:
                    raise ValueError('Missing per-item lastmod in change list')

                try:
                    # Use dateutil.parser for better compatibility with Python 3.6
                    lastmod_dt = parse_datetime(lastmod.text)
                except ValueError as exc:
                    raise ValueError(f'Invalid lastmod format in change list: {lastmod.text}') from exc

                md_elem = url_elem.find('{http://www.openarchives.org/rs/terms/}md')
                if md_elem is None:
                    raise ValueError('Missing rs:md element with change attribute in change list')

                action = md_elem.get('change')
                if action not in ('created', 'updated', 'deleted'):
                    raise ValueError(f'Unsupported rs:md@change value: {action}')

                changes.append((action, loc.text, lastmod_dt))

        logger.info(f'Found {len(changes)} changes in change list')

        for change in changes:
            yield change

    def fetch_researcher_data(self, json_url: str) -> Dict:
        """
        Fetch individual researcher data from JSON URL

        Args:
            json_url: URL to researcher JSON data

        Returns:
            Researcher data dictionary

        Raises:
            requests.RequestException: If request fails
        """
        logger.debug(f'Fetching researcher data from: {json_url}')

        try:
            response = self.session.get(json_url, timeout=self.timeout)
            response.raise_for_status()

            if not response.content:
                logger.warning(f'Empty JSON response from {json_url}; treating as empty document')
                data = {}
            else:
                data = response.json()

            data['_source_url'] = json_url
            return data
        except requests.RequestException as e:
            logger.exception(f'Failed to fetch researcher data from {json_url}: {e}')
            raise

    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
