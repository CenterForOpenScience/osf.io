"""
KAKEN suggestion functions using Elasticsearch
"""
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

from ..utils import to_msfullname, contributors_self_first, build_display_fullname
from .elasticsearch import KakenElasticsearchService, KakenElasticsearchError
from .constants import (
    HAIBUNKIKAN_CD,
    HAIBUNKIKAN_MEI_JA,
    HAIBUNKIKAN_MEI_EN,
    PROGRAM_NAME_JA,
    PROGRAM_NAME_EN,
    DEFAULT_FUNDING_STREAM_CODE,
    KAKENHI_PROJECT_PREFIX,
)
from .review_map import lookup_small
from website.project.metadata.schemas import from_json as load_schema_json
from addons.metadata import settings
from framework.auth.core import _get_current_user

logger = logging.getLogger(__name__)

# Cache for e-Rad field mapping: '189' -> ('ライフサイエンス','Life Science')
_ERAD_FIELD_MAP = None


def _erad_field_map() -> Dict[str, Tuple[str, str]]:
    global _ERAD_FIELD_MAP
    if _ERAD_FIELD_MAP is not None:
        return _ERAD_FIELD_MAP
    try:
        schema = load_schema_json('e-rad-metadata-1.json')
    except Exception:
        # Surface the error; caller tests run in Docker where this file exists
        raise

    mapping: Dict[str, Tuple[str, str]] = {}
    pages = schema.get('pages') or []
    for page in pages:
        if not isinstance(page, dict):
            continue
        for q in page.get('questions') or []:
            if not isinstance(q, dict):
                continue
            if q.get('qid') == 'project-research-field':
                for opt in q.get('options') or []:
                    tip = (opt.get('tooltip') or '').split('|')
                    if len(tip) >= 3:
                        ja = tip[0].strip()
                        en = tip[1].strip()
                        code = tip[2].strip()
                        mapping[code] = (ja, en)
                _ERAD_FIELD_MAP = mapping
                return _ERAD_FIELD_MAP
    _ERAD_FIELD_MAP = mapping
    return _ERAD_FIELD_MAP


def suggest_kaken(key: str, keyword: str, node) -> List[Dict[str, Any]]:
    """
    Main suggestion function for KAKEN data using Elasticsearch

    Args:
        key: The suggestion key (e.g., 'kaken:kenkyusha_shimei')
        keyword: Search keyword for filtering
        node: OSF node object containing contributors with ERAD IDs

    Returns:
        List of suggestion dictionaries with 'key' and 'value' fields
    """
    # Check if KAKEN functionality is enabled
    if settings.KAKEN_ELASTIC_URI is None:
        logger.debug('KAKEN functionality disabled (KAKEN_ELASTIC_URI is None)')
        return []

    if not key.startswith('kaken:'):
        logger.warning(f'Invalid key format: {key}')
        return []

    filter_field_name = key[6:]  # Remove 'kaken:' prefix
    # Get current user from session to prioritize self in results
    current_user = _get_current_user()
    candidates = _kaken_candidates_for_node(node, current_user=current_user, **{filter_field_name: keyword})

    res = []
    for candidate in candidates:
        res.append({
            'key': key,
            'value': candidate,
        })
    return res


def kaken_candidates(user_erad: str, **pred) -> List[Dict[str, Any]]:
    """
    Get KAKEN candidates for a specific user's ERAD ID using Elasticsearch

    Args:
        user_erad: User's ERAD ID
        **pred: Additional filtering predicates (e.g., kenkyusha_shimei='keyword')

    Returns:
        List of candidate dictionaries with researcher/project data
    """
    # Check if KAKEN functionality is enabled
    if settings.KAKEN_ELASTIC_URI is None:
        logger.debug('KAKEN functionality disabled (KAKEN_ELASTIC_URI is None)')
        return []

    if not user_erad:
        logger.warning('Empty user_erad provided')
        return []

    logger.info(f'Searching KAKEN Elasticsearch with user_erad: {user_erad}, pred: {pred}')

    # Initialize Elasticsearch service
    es_service = KakenElasticsearchService(
        hosts=[settings.KAKEN_ELASTIC_URI],
        index_name=settings.KAKEN_ELASTIC_INDEX,
        analyzer_config=settings.KAKEN_ELASTIC_ANALYZER_CONFIG,
        **settings.KAKEN_ELASTIC_KWARGS
    )

    try:
        # Search for researcher by ERAD ID
        researcher_data = es_service.get_researcher_by_erad(user_erad)
        if not researcher_data:
            logger.info(f'No researcher found for ERAD ID: {user_erad}')
            return []

        # Transform researcher data to candidates
        collaborator_name_cache: Dict[str, Optional[Dict[str, str]]] = {}
        candidates = _transform_researcher_to_candidates(
            researcher_data,
            es_service,
            collaborator_name_cache,
        )

        # Apply filtering predicates
        filtered_candidates = []
        for candidate in candidates:
            target = True
            for filter_field_name, keyword in pred.items():
                if filter_field_name in candidate:
                    candidate_value = candidate[filter_field_name]
                    # Handle different types of values
                    if candidate_value is None:
                        target = False
                        break
                    elif isinstance(candidate_value, str):
                        if keyword.lower() not in candidate_value.lower():
                            target = False
                            break
                    elif isinstance(candidate_value, list):
                        # Check if keyword matches any item in the list
                        found = False
                        for item in candidate_value:
                            if isinstance(item, str) and keyword.lower() in item.lower():
                                found = True
                                break
                        if not found:
                            target = False
                            break
                    else:
                        # For other types, convert to string and check
                        if keyword.lower() not in str(candidate_value).lower():
                            target = False
                            break
                else:
                    logger.warning(f'Filter field {filter_field_name} not found in candidate: {candidate}')
                    target = False
                    break

            if target:
                filtered_candidates.append(candidate)

        logger.info(f'Found {len(filtered_candidates)} candidates for user_erad: {user_erad}')
        return filtered_candidates

    finally:
        es_service.close()


def _kaken_candidates_for_node(node, current_user=None, **pred) -> List[Dict[str, Any]]:
    """
    Get KAKEN candidates for all contributors in a node

    Args:
        node: OSF node object
        **pred: Filtering predicates

    Returns:
        Flattened list of candidates from all contributors
    """
    all_candidates = []

    # Iterate contributors with current user first (if available)
    ordered_contributors = contributors_self_first(node, current_user=current_user)

    for user in ordered_contributors:
        if user.erad is not None and user.erad != '':
            user_candidates = kaken_candidates(user.erad, **pred)
            all_candidates.extend(user_candidates)

    return all_candidates


def _transform_researcher_to_candidates(
    researcher_data: Dict[str, Any],
    es_service: KakenElasticsearchService,
    collaborator_name_cache: Dict[str, Optional[Dict[str, str]]],
) -> List[Dict[str, Any]]:
    """
    Transform Elasticsearch researcher data to candidate format

    Args:
        researcher_data: Researcher data from Elasticsearch

    Returns:
        List of candidate dictionaries
    """
    candidates = []

    # Extract basic researcher information
    erad_id = researcher_data.get('id:person:erad', '')

    # Process researcher name
    researcher_name_info = _extract_name_info(researcher_data)

    # Process institution information
    institution_info = _extract_institution_info(researcher_data)

    # Process projects
    work_projects = researcher_data.get('work:project', [])
    if not isinstance(work_projects, list):
        work_projects = []

    # If no projects, create a basic researcher candidate
    if not work_projects:
        candidate = {
            'erad': erad_id[0] if isinstance(erad_id, list) else erad_id,
            'kadai_id': '',
            'nendo': '',
            'japan_grant_number': '',
            'funding_stream_code': DEFAULT_FUNDING_STREAM_CODE,
            'haibunkikan_cd': HAIBUNKIKAN_CD,
            'haibunkikan_mei': f'{HAIBUNKIKAN_MEI_JA}|{HAIBUNKIKAN_MEI_EN}',
            'program_name_ja': PROGRAM_NAME_JA,
            'program_name_en': PROGRAM_NAME_EN,
            # TODO: Extract and properly process research field (bunya) information from project data
            'bunya_cd': '',
            'bunya_mei': '',
            'bunya_mei_en': '',
        }
        candidate.update(researcher_name_info)
        candidate.update(institution_info)
        candidates.append(candidate)
        return candidates

    # Process each project
    primary_erad = erad_id[0] if isinstance(erad_id, list) else erad_id

    for project in work_projects:
        if not isinstance(project, dict):
            continue

        # Extract project IDs (may be multiple)
        project_ids = _extract_project_ids(project)

        # If no project IDs found, create one candidate with empty ID
        if not project_ids:
            project_ids = ['']

        # Create a candidate for each project ID
        for project_id in project_ids:
            # Remove KAKENHI-PROJECT- prefix if present
            if project_id.startswith(KAKENHI_PROJECT_PREFIX):
                project_id = project_id[len(KAKENHI_PROJECT_PREFIX):]

            project_base = _build_project_candidate_base(project, project_id)

            primary_candidate = project_base.copy()
            primary_candidate['erad'] = primary_erad
            primary_candidate.update(researcher_name_info)
            primary_candidate.update(institution_info)
            candidates.append(primary_candidate)

            collaborator_candidates = _extract_collaborator_candidates(
                project,
                project_base,
                primary_erad,
                es_service,
                collaborator_name_cache,
            )
            candidates.extend(collaborator_candidates)

    return candidates


def _extract_bunya_from_review_section(project: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Extract bunya (research field) from review_section.

    Returns most specific level if available (rank: 大区分=1, 中区分=2, 小区分=3).
    Output: {'code': 'NNNNN', 'name_ja': '...', 'name_en': '...'}
    """
    review = project.get('review_section')
    if not isinstance(review, list):
        return None

    best: Optional[Tuple[int, Dict[str, str]]] = None
    for item in review:
        if not isinstance(item, dict):
            continue
        hr = item.get('humanReadableValue')
        if not isinstance(hr, list):
            continue
        # Map by lang for pairing ja/en
        langs = {}
        for hv in hr:
            if isinstance(hv, dict):
                langs[hv.get('lang')] = hv

        ja = langs.get('ja')
        if not isinstance(ja, dict):
            continue
        text_ja = ja.get('text') or ''
        # Accept optional spaces and both ASCII/JP colon
        m = re.match(r'^(小区分|中区分|大区分)\s*(\d{5})\s*[:：]\s*(.+)$', text_ja)
        if not m:
            # Not a section label with 区分
            continue
        level, code, name_ja = m.group(1), m.group(2), m.group(3).strip()
        rank = {'大区分': 1, '中区分': 2, '小区分': 3}[level]

        name_en = ''
        en = langs.get('en')
        if isinstance(en, dict):
            text_en = en.get('text') or ''
            if ':' in text_en:
                name_en = text_en.split(':', 1)[1].strip()

        res = {'code': code, 'name_ja': name_ja, 'name_en': name_en}
        if best is None or rank > best[0]:
            best = (rank, res)

    return best[1] if best else None


def _extract_name_info(researcher_data: Dict[str, Any]) -> Dict[str, str]:
    """Extract and format name information from researcher data"""
    # TODO: Review field naming conventions - consider using KAKEN vocabulary instead of e-Rad-based symbols
    # (e.g., kenkyukikan_mei_ja -> institution_name_ja for better semantic clarity)
    name_info = {
        'kenkyusha_shimei': '',
        'kenkyusha_shimei_ja': '',
        'kenkyusha_shimei_en': '',
        'kenkyusha_shimei_ja_msfullname': '',
        'kenkyusha_shimei_en_msfullname': '',
        'kenkyusha_shimei_ja_parts': {},
        'kenkyusha_shimei_en_parts': {},
        'display_fullname': '',
    }

    # Process main name
    main_name = researcher_data.get('name', {})
    if isinstance(main_name, dict):
        name_info.update(_process_name_object(main_name, 'main'))

    # Process names array
    names = researcher_data.get('names', [])
    if isinstance(names, list):
        for name_obj in names:
            if isinstance(name_obj, dict):
                processed_name = _process_name_object(name_obj, 'names')
                # Use the first valid name found
                for key, value in processed_name.items():
                    if key not in name_info:
                        continue
                    if value and not name_info[key]:
                        name_info[key] = value

    # Build combined name formats
    if name_info['kenkyusha_shimei_ja'] and name_info['kenkyusha_shimei_en']:
        name_info['kenkyusha_shimei'] = f"{name_info['kenkyusha_shimei_ja']}||{name_info['kenkyusha_shimei_en']}"
    elif name_info['kenkyusha_shimei_ja']:
        name_info['kenkyusha_shimei'] = f"{name_info['kenkyusha_shimei_ja']}||"
    elif name_info['kenkyusha_shimei_en']:
        name_info['kenkyusha_shimei'] = f"||{name_info['kenkyusha_shimei_en']}"

    display_name = build_display_fullname(
        name_info.get('kenkyusha_shimei_ja_parts') or {},
        name_info.get('kenkyusha_shimei_en_parts') or {},
    )
    name_info['display_fullname'] = display_name

    return name_info


def _process_name_object(name_obj: Dict[str, Any], source: str) -> Dict[str, str]:
    """Process a single name object from researcher data"""
    processed = {
        'kenkyusha_shimei_ja': '',
        'kenkyusha_shimei_en': '',
        'kenkyusha_shimei_ja_msfullname': '',
        'kenkyusha_shimei_en_msfullname': '',
    }

    # Extract human readable values
    human_readable = name_obj.get('humanReadableValue', [])
    if not isinstance(human_readable, list):
        human_readable = []

    # Extract family and given names
    family_names = name_obj.get('name:familyName', [])
    given_names = name_obj.get('name:givenName', [])

    if not isinstance(family_names, list):
        family_names = []
    if not isinstance(given_names, list):
        given_names = []

    # Process by language
    for lang in ['ja', 'en']:
        family_name = ''
        given_name = ''

        # Find family name for this language
        for fn in family_names:
            if isinstance(fn, dict) and fn.get('lang') == lang:
                family_name = fn.get('text', '').strip()
                break

        # Find given name for this language
        for gn in given_names:
            if isinstance(gn, dict) and gn.get('lang') == lang:
                given_name = gn.get('text', '').strip()
                break

        name_dict = {
            'last': family_name,
            'middle': '',
            'first': given_name,
        }
        processed[f'kenkyusha_shimei_{lang}_parts'] = name_dict

        if family_name and given_name:
            processed[f'kenkyusha_shimei_{lang}'] = f'{family_name}|{given_name}'

        if family_name or given_name:
            try:
                msfullname = to_msfullname(name_dict, lang)
                processed[f'kenkyusha_shimei_{lang}_msfullname'] = msfullname
            except ValueError as e:
                logger.warning(f'Error creating MSFullName for {lang}: {e}')

    return processed


def _get_current_affiliation(affiliations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Select the most current affiliation based on sequence number

    Args:
        affiliations: List of affiliation objects

    Returns:
        dict: Affiliation with smallest sequence number (most recent) or None
    """
    if not affiliations:
        return None

    # Find affiliation with smallest sequence number (most recent)
    min_sequence = float('inf')
    current_affiliation = None

    for affiliation in affiliations:
        if not isinstance(affiliation, dict):
            continue

        sequence = affiliation.get('sequence', float('inf'))
        if sequence < min_sequence:
            min_sequence = sequence
            current_affiliation = affiliation

    return current_affiliation


def _extract_institution_info(researcher_data: Dict[str, Any]) -> Dict[str, str]:
    """Extract institution information from researcher data"""
    institution_info = {
        'kenkyukikan_mei': '',
        'kenkyukikan_mei_ja': '',
        'kenkyukikan_mei_en': '',
    }

    # Get current affiliation from affiliations:history
    affiliations = researcher_data.get('affiliations:history', [])
    if isinstance(affiliations, list) and affiliations:
        # Select the most current affiliation based on dates
        affiliation = _get_current_affiliation(affiliations)
        if isinstance(affiliation, dict):
            institution = affiliation.get('affiliation:institution', {})
            if isinstance(institution, dict):
                human_readable = institution.get('humanReadableValue', [])
                if isinstance(human_readable, list):
                    for hr in human_readable:
                        if isinstance(hr, dict):
                            lang = hr.get('lang', '')
                            text = hr.get('text', '').strip()
                            if lang == 'ja':
                                institution_info['kenkyukikan_mei_ja'] = text
                            elif lang == 'en':
                                institution_info['kenkyukikan_mei_en'] = text

    # Build combined institution format
    if institution_info['kenkyukikan_mei_ja'] and institution_info['kenkyukikan_mei_en']:
        institution_info['kenkyukikan_mei'] = f"{institution_info['kenkyukikan_mei_ja']}|{institution_info['kenkyukikan_mei_en']}"
    elif institution_info['kenkyukikan_mei_ja']:
        institution_info['kenkyukikan_mei'] = f"{institution_info['kenkyukikan_mei_ja']}|"
    elif institution_info['kenkyukikan_mei_en']:
        institution_info['kenkyukikan_mei'] = f"|{institution_info['kenkyukikan_mei_en']}"

    return institution_info


def _extract_project_ids(project: Dict[str, Any]) -> List[str]:
    """Extract project IDs from project data (may be multiple)"""
    record_source = project.get('recordSource', {})
    if isinstance(record_source, dict):
        project_ids = record_source.get('id:project:kakenhi', [])
        # Handle both string and list cases
        if isinstance(project_ids, str):
            return [project_ids] if project_ids else []
        elif isinstance(project_ids, list):
            return [pid for pid in project_ids if isinstance(pid, str) and pid]
    return []


def _extract_project_year(project: Dict[str, Any]) -> str:
    """Extract project year from project data"""
    # Try to get year from project status
    project_status = project.get('projectStatus', {})
    if isinstance(project_status, dict):
        fiscal_year = project_status.get('fiscal:year', {})
        if isinstance(fiscal_year, dict):
            common_era_year = fiscal_year.get('commonEra:year', '')
            if common_era_year:
                return str(common_era_year)

    # Try to get year from since/until dates
    for date_field in ['since', 'until']:
        date_obj = project.get(date_field, {})
        if isinstance(date_obj, dict):
            fiscal_year = date_obj.get('fiscal:year', {})
            if isinstance(fiscal_year, dict):
                common_era_year = fiscal_year.get('commonEra:year', '')
                if common_era_year:
                    return str(common_era_year)

    return ''


def _format_japan_grant_number(project_id: str) -> str:
    """Format project ID as Japan grant number"""
    if not project_id:
        return ''
    if project_id.startswith('JP'):
        return project_id
    else:
        return f'JP{project_id}'


def _extract_project_title_info(project: Dict[str, Any]) -> Dict[str, str]:
    """Extract project title information from project data"""
    title_info = {
        'kadai_mei': '',
        'kadai_mei_ja': '',
        'kadai_mei_en': '',
    }

    # Extract title information
    titles = project.get('title', [])
    if not isinstance(titles, list):
        titles = []

    for title in titles:
        if isinstance(title, dict):
            human_readable = title.get('humanReadableValue', [])
            if isinstance(human_readable, list):
                for hr in human_readable:
                    if isinstance(hr, dict):
                        lang = hr.get('lang', '')
                        text = hr.get('text', '').strip()
                        if lang == 'ja':
                            title_info['kadai_mei_ja'] = text
                        elif lang == 'en':
                            title_info['kadai_mei_en'] = text

    # Build combined title format
    if title_info['kadai_mei_ja'] and title_info['kadai_mei_en']:
        title_info['kadai_mei'] = f"{title_info['kadai_mei_ja']}|{title_info['kadai_mei_en']}"
    elif title_info['kadai_mei_ja']:
        title_info['kadai_mei'] = f"{title_info['kadai_mei_ja']}|"
    elif title_info['kadai_mei_en']:
        title_info['kadai_mei'] = f"|{title_info['kadai_mei_en']}"

    return title_info


def _build_project_candidate_base(project: Dict[str, Any], project_id: str) -> Dict[str, str]:
    base = {
        'kadai_id': project_id,
        'nendo': _extract_project_year(project),
        'japan_grant_number': _format_japan_grant_number(project_id),
        'funding_stream_code': DEFAULT_FUNDING_STREAM_CODE,
        'haibunkikan_cd': HAIBUNKIKAN_CD,
        'haibunkikan_mei': f'{HAIBUNKIKAN_MEI_JA}|{HAIBUNKIKAN_MEI_EN}',
        'program_name_ja': PROGRAM_NAME_JA,
        'program_name_en': PROGRAM_NAME_EN,
        'bunya_cd': '',
        'bunya_mei': '',
        'bunya_mei_en': '',
    }

    base.update(_extract_project_title_info(project))

    bunya = _extract_bunya_from_review_section(project)
    _apply_bunya_info(base, bunya)

    return base


def _apply_bunya_info(candidate: Dict[str, Any], bunya: Optional[Dict[str, str]]):
    if not bunya:
        return

    rec = lookup_small(bunya.get('code', ''))
    if rec:
        lg = rec.get('large_code', '')
        m_lg = re.match(r'^[A-Z]?(\d{3})$', str(lg))
        candidate['bunya_cd'] = m_lg.group(1) if m_lg else ''
        ja_en = _erad_field_map().get(candidate['bunya_cd']) if candidate['bunya_cd'] else None
        if ja_en:
            candidate['bunya_mei'] = ja_en[0]
            candidate['bunya_mei_en'] = ja_en[1]
        else:
            candidate['bunya_mei'] = rec.get('large_name_ja', '') or bunya.get('name_ja', '')
            candidate['bunya_mei_en'] = rec.get('large_name_en', '') or bunya.get('name_en', '')
        return

    candidate['bunya_mei'] = bunya.get('name_ja', '')
    candidate['bunya_mei_en'] = bunya.get('name_en', '')


def _extract_collaborator_candidates(
    project: Dict[str, Any],
    project_base: Dict[str, Any],
    primary_erad: str,
    es_service: KakenElasticsearchService,
    collaborator_name_cache: Dict[str, Optional[Dict[str, str]]],
) -> List[Dict[str, Any]]:
    members = project.get('member', [])
    if not isinstance(members, list):
        return []

    collaborator_candidates: List[Dict[str, Any]] = []

    for entry in members:
        if not isinstance(entry, dict):
            continue

        iterable = entry.get('list') if isinstance(entry.get('list'), list) else [entry]
        for member in iterable:
            if not isinstance(member, dict):
                continue
            member_erad = _extract_member_erad(member)
            if member_erad and member_erad == primary_erad:
                continue

            candidate = _build_member_candidate(
                member,
                project_base,
                primary_erad,
                es_service,
                collaborator_name_cache,
            )
            if candidate:
                collaborator_candidates.append(candidate)

    return collaborator_candidates


def _extract_member_erad(member: Dict[str, Any]) -> str:
    erad = member.get('id:person:erad')
    if isinstance(erad, list):
        return erad[0] if erad else ''
    if isinstance(erad, str):
        return erad
    return ''


def _build_member_candidate(
    member: Dict[str, Any],
    project_base: Dict[str, Any],
    primary_erad: str,
    es_service: KakenElasticsearchService,
    collaborator_name_cache: Dict[str, Optional[Dict[str, str]]],
) -> Optional[Dict[str, Any]]:
    candidate = project_base.copy()
    candidate['kaken_collaborator'] = True
    candidate['source_erad'] = primary_erad
    candidate['erad'] = _extract_member_erad(member)
    candidate['kaken_role'] = _extract_member_role(member)

    name_info = _extract_member_name_info(member)
    candidate.update(name_info)

    if candidate['erad'] and not candidate.get('kenkyusha_shimei_en'):
        enriched = _enrich_member_name_from_es(
            candidate['erad'],
            es_service,
            collaborator_name_cache,
        )
        if enriched:
            _apply_enriched_member_name(candidate, enriched)

    institution_info = _extract_member_institution_info(member)
    candidate.update(institution_info)

    if not any(
        candidate.get(field)
        for field in (
            'erad',
            'kenkyusha_shimei_ja_msfullname',
            'kenkyusha_shimei_en_msfullname',
            'kenkyusha_shimei',
        )
    ):
        return None

    return candidate


def _enrich_member_name_from_es(
    member_erad: str,
    es_service: KakenElasticsearchService,
    collaborator_name_cache: Dict[str, Optional[Dict[str, str]]],
) -> Optional[Dict[str, str]]:
    if member_erad in collaborator_name_cache:
        return collaborator_name_cache[member_erad]

    try:
        researcher_data = es_service.get_researcher_by_erad(member_erad)
    except KakenElasticsearchError as exc:
        logger.warning(
            'Failed to enrich collaborator name via KAKEN for ERAD %s: %s',
            member_erad,
            exc,
        )
        collaborator_name_cache[member_erad] = None
        return None

    if not researcher_data:
        collaborator_name_cache[member_erad] = None
        return None

    name_info = _extract_name_info(researcher_data)
    if not name_info.get('kenkyusha_shimei_en'):
        collaborator_name_cache[member_erad] = None
        return None

    collaborator_name_cache[member_erad] = name_info
    return name_info


def _apply_enriched_member_name(candidate: Dict[str, Any], enriched: Dict[str, Any]):
    if enriched.get('kenkyusha_shimei_en'):
        candidate['kenkyusha_shimei_en'] = enriched['kenkyusha_shimei_en']

    if enriched.get('kenkyusha_shimei_en_msfullname'):
        candidate['kenkyusha_shimei_en_msfullname'] = enriched['kenkyusha_shimei_en_msfullname']

    en_parts = enriched.get('kenkyusha_shimei_en_parts')
    if isinstance(en_parts, dict):
        candidate['kenkyusha_shimei_en_parts'] = en_parts

    _refresh_member_display_fields(candidate)


def _refresh_member_display_fields(candidate: Dict[str, Any]):
    ja_entry = candidate.get('kenkyusha_shimei_ja', '')
    en_entry = candidate.get('kenkyusha_shimei_en', '')

    if ja_entry and en_entry:
        candidate['kenkyusha_shimei'] = f'{ja_entry}||{en_entry}'
    elif ja_entry:
        candidate['kenkyusha_shimei'] = f'{ja_entry}||'
    elif en_entry:
        candidate['kenkyusha_shimei'] = f'||{en_entry}'
    else:
        candidate['kenkyusha_shimei'] = ''

    candidate['display_fullname'] = build_display_fullname(
        candidate.get('kenkyusha_shimei_ja_parts') or {},
        candidate.get('kenkyusha_shimei_en_parts') or {},
    )


def _extract_member_role(member: Dict[str, Any]) -> str:
    roles = member.get('role', [])
    if not isinstance(roles, list):
        return ''
    for role in roles:
        if isinstance(role, dict):
            value = role.get('code:roleInProject:kakenhi')
            if value:
                return value
    return ''


def _extract_member_name_info(member: Dict[str, Any]) -> Dict[str, str]:
    info = {
        'kenkyusha_shimei': '',
        'kenkyusha_shimei_ja': '',
        'kenkyusha_shimei_en': '',
        'kenkyusha_shimei_ja_msfullname': '',
        'kenkyusha_shimei_en_msfullname': '',
        'kenkyusha_shimei_ja_parts': {},
        'kenkyusha_shimei_en_parts': {},
        'display_fullname': '',
    }

    names = member.get('person:name', [])
    if not isinstance(names, list):
        names = []

    def pick_by_lang(lang_codes):
        for lang in lang_codes:
            for entry in names:
                if isinstance(entry, dict) and entry.get('lang') == lang:
                    text = (entry.get('text') or '').strip()
                    if text:
                        return text
        return ''

    ja_name = pick_by_lang(['ja', 'ja-JP'])
    en_name = pick_by_lang(['en', 'en-US', 'en-GB'])

    _populate_member_name_fields(info, ja_name, en_name)
    return info


def _populate_member_name_fields(info: Dict[str, str], ja_name: str, en_name: str):
    def apply_parts(full_name: str, lang: str):
        parts = _split_name_parts(full_name, lang)
        entry = ''
        if parts['last'] or parts['first']:
            entry = f"{parts['last']}|{parts['first']}".strip('|')
        msfull = _member_msfullname(parts, lang, full_name)
        return entry, msfull, parts

    if ja_name:
        ja_entry, ja_ms, ja_parts = apply_parts(ja_name, 'ja')
        if ja_entry:
            info['kenkyusha_shimei_ja'] = ja_entry
        info['kenkyusha_shimei_ja_msfullname'] = ja_ms
        info['kenkyusha_shimei_ja_parts'] = ja_parts

    if en_name:
        en_entry, en_ms, en_parts = apply_parts(en_name, 'en')
        if en_entry:
            info['kenkyusha_shimei_en'] = en_entry
        info['kenkyusha_shimei_en_msfullname'] = en_ms
        info['kenkyusha_shimei_en_parts'] = en_parts

    if info['kenkyusha_shimei_ja'] and info['kenkyusha_shimei_en']:
        info['kenkyusha_shimei'] = f"{info['kenkyusha_shimei_ja']}||{info['kenkyusha_shimei_en']}"
    elif info['kenkyusha_shimei_ja']:
        info['kenkyusha_shimei'] = f"{info['kenkyusha_shimei_ja']}||"
    elif info['kenkyusha_shimei_en']:
        info['kenkyusha_shimei'] = f"||{info['kenkyusha_shimei_en']}"

    display_name = build_display_fullname(
        info.get('kenkyusha_shimei_ja_parts') or {},
        info.get('kenkyusha_shimei_en_parts') or {},
    )
    info['display_fullname'] = display_name


def _split_name_parts(full_name: str, lang: str) -> Dict[str, str]:
    if not full_name:
        return {'last': '', 'middle': '', 'first': ''}

    tokens = [t for t in re.split(r'[\s\u3000]+', full_name.strip()) if t]
    if not tokens:
        return {'last': '', 'middle': '', 'first': ''}

    if lang == 'ja':
        last = tokens[0]
        first = ''.join(tokens[1:]) if len(tokens) > 1 else ''
        return {'last': last, 'middle': '', 'first': first}

    if len(tokens) == 1:
        return {'last': '', 'middle': '', 'first': tokens[0]}
    if len(tokens) == 2:
        return {'last': tokens[1], 'middle': '', 'first': tokens[0]}
    return {
        'last': tokens[-1],
        'middle': ' '.join(tokens[1:-1]),
        'first': tokens[0],
    }


def _member_msfullname(parts: Dict[str, str], lang: str, fallback: str) -> str:
    if parts['last'] and parts['first']:
        try:
            return to_msfullname(parts, lang)
        except ValueError:
            pass
    if lang == 'ja':
        return fallback.replace(' ', '').replace('\u3000', '').strip()
    return fallback.strip()


def _extract_member_institution_info(member: Dict[str, Any]) -> Dict[str, str]:
    info = {
        'kenkyukikan_mei': '',
        'kenkyukikan_mei_ja': '',
        'kenkyukikan_mei_en': '',
    }

    institution = member.get('institution:name', [])
    if not isinstance(institution, list):
        institution = []

    for entry in institution:
        if not isinstance(entry, dict):
            continue
        lang = entry.get('lang', '')
        text = (entry.get('text') or '').strip()
        if not text:
            continue
        if lang == 'ja' and not info['kenkyukikan_mei_ja']:
            info['kenkyukikan_mei_ja'] = text
        elif lang == 'en' and not info['kenkyukikan_mei_en']:
            info['kenkyukikan_mei_en'] = text

    if info['kenkyukikan_mei_ja'] and info['kenkyukikan_mei_en']:
        info['kenkyukikan_mei'] = f"{info['kenkyukikan_mei_ja']}|{info['kenkyukikan_mei_en']}"
    elif info['kenkyukikan_mei_ja']:
        info['kenkyukikan_mei'] = f"{info['kenkyukikan_mei_ja']}|"
    elif info['kenkyukikan_mei_en']:
        info['kenkyukikan_mei'] = f"|{info['kenkyukikan_mei_en']}"

    return info
