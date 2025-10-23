import logging
from typing import List, Dict, Any, Optional, Callable


logger = logging.getLogger(__name__)


PERSON_KEYS = {
    # Contributor
    'contributor:erad', 'contributor:name', 'contributor:name-ja', 'contributor:name-en',
    'contributor:affiliated-institution-name',
    # ERAD (researcher)
    'erad:kenkyusha_no', 'erad:kenkyusha_shimei', 'erad:kenkyusha_shimei_ja', 'erad:kenkyusha_shimei_en',
    # KAKEN (researcher)
    'kaken:erad', 'kaken:kenkyusha_shimei', 'kaken:kenkyusha_shimei_ja', 'kaken:kenkyusha_shimei_en',
}
PROJECT_KEYS = {
    # ERAD (project)
    'erad:kadai_id', 'erad:japan_grant_number', 'erad:nendo', 'erad:kadai_mei',
    'erad:program_name_ja', 'erad:program_name_en',
    'erad:haibunkikan_cd', 'erad:haibunkikan_mei',
    'erad:bunya_cd', 'erad:bunya_mei',
    # KAKEN (project)
    'kaken:kadai_id', 'kaken:japan_grant_number', 'kaken:nendo', 'kaken:kadai_mei',
    'kaken:program_name_ja', 'kaken:program_name_en',
    'kaken:haibunkikan_cd', 'kaken:haibunkikan_mei',
    'kaken:bunya_cd', 'kaken:bunya_mei', 'kaken:bunya_mei_en',
}


def resolve_person_id(value: Dict[str, Any]) -> str:
    """Resolve person identifier from a suggestion value/candidate.

    Prefers explicit ERAD identifiers available from either source shape.
    """
    return (
        value.get('erad')
        or value.get('kenkyusha_no')
        or ''
    )


def resolve_project_id(value: Dict[str, Any]) -> str:
    """Resolve project identifier from a suggestion value/candidate."""
    return (
        value.get('kadai_id')
        or value.get('japan_grant_number')
        or ''
    )


def to_msfullname(name, lang):
    names = []
    if 'last' not in name:
        raise ValueError('Invalid name: {}'.format(name))
    names.append(name['last'])
    if 'middle' in name:
        names.append(name['middle'])
    if 'first' not in name:
        raise ValueError('Invalid name: {}'.format(name))
    names.append(name['first'])
    names = [n.strip() for n in names]
    if lang == 'ja':
        return ''.join(names)
    names = [n for n in names if len(n) > 0]
    return ' '.join(names[::-1])


def format_display_fullname(name_ja: str, name_en: str) -> str:
    """Return a single-line display name combining Japanese and English variants."""
    ja = (name_ja or '').strip()
    en = (name_en or '').strip()
    if ja and en:
        return f'{ja} ({en})'
    return ja or en


def name_parts_to_display(name_parts: Dict[str, str], lang: str) -> str:
    """Join structured name parts into a displayable string for the given language."""
    if not isinstance(name_parts, dict):
        return ''
    last = (name_parts.get('last') or '').strip()
    middle = (name_parts.get('middle') or '').strip()
    first = (name_parts.get('first') or '').strip()
    if lang == 'ja':
        order = [last, middle, first]
    else:
        order = [first, middle, last]
    parts = [part for part in order if part]
    return ' '.join(parts)


def build_display_fullname(name_ja_parts: Dict[str, str], name_en_parts: Dict[str, str]) -> str:
    ja_display = name_parts_to_display(name_ja_parts, 'ja')
    en_display = name_parts_to_display(name_en_parts, 'en')
    return format_display_fullname(ja_display, en_display)


def contributors_self_first(node, current_user=None) -> List[Any]:
    """
    Return contributors ordered with the current user first, then others.

    If current_user is None or not among contributors, returns node.contributors as-is.
    """
    contributors = list(node.contributors or [])

    if not current_user:
        return contributors

    result = []
    rest = []
    for u in contributors:
        if u == current_user:
            result.append(u)
        else:
            rest.append(u)
    if not result:
        return contributors
    return result + rest
def _candidate_owner_erad(data: Dict[str, Any]) -> Optional[str]:
    """Return ERAD identifier from suggestion value or candidate dict."""
    erad = data.get('erad')
    if isinstance(erad, str) and erad:
        return erad
    kenkyusha_no = data.get('kenkyusha_no')
    if isinstance(kenkyusha_no, str) and kenkyusha_no:
        return kenkyusha_no
    return None


def _candidate_year(candidate: Dict[str, Any], year_field: str = 'nendo') -> int:
    try:
        year = candidate.get(year_field, '')
        return int(year) if year else 0
    except (ValueError, TypeError):
        logger.warning(
            (
                'Invalid year format in candidate: %s, %s: %s'
            ),
            candidate.get('kadai_id', 'unknown'), year_field, candidate.get(year_field, 'N/A'),
            exc_info=True,
        )
        return 0


def classify_key_mode(key: str) -> Optional[str]:
    """Classify a suggestion key as 'person', 'project', or None (unknown).

    Expects keys like 'erad:kenkyusha_no' / 'kaken:kadai_id'.
    """
    if not isinstance(key, str) or ':' not in key:
        return None
    if key in PERSON_KEYS:
        return 'person'
    if key in PROJECT_KEYS:
        return 'project'
    return None


def classify_mode_for_keys(keys: List[str]) -> Optional[str]:
    """Return 'person' if all keys are person, 'project' if all project, else None (mixed/unknown)."""
    modes = {classify_key_mode(k) for k in keys if isinstance(k, str)}
    modes.discard(None)
    if not modes:
        return None
    if len(modes) == 1:
        return next(iter(modes))
    return None


def order_candidates_by_contributors(
    candidates: List[Dict[str, Any]],
    contributor_erads_order: List[str],
    year_field: str = 'nendo',
    id_field: str = 'kadai_id',
    id_resolver: Optional[Callable[[Dict[str, Any]], Optional[str]]] = None,
) -> List[Dict[str, Any]]:
    """Order project/person candidates by contributor order and year desc, then dedupe by ID.

    - contributor order: current user first (precomputed), then others
    - within each contributor: year desc
    - dedup: by id_field (or id_resolver), first occurrence wins
    """
    def _resolve_id(c: Dict[str, Any]) -> str:
        if id_resolver:
            v = id_resolver(c)
            if v:
                return v
        return (
            c.get(id_field)
            or c.get(id_field.upper(), '')
            or c.get('kadai_id', '')
            or c.get('KADAI_ID', '')
            or c.get('japan_grant_number', '')
            or ''
        )

    return _order_items_by_contributors(
        candidates,
        contributor_erads_order,
        year_field=year_field,
        key_list=None,
        as_suggestions=False,
        id_resolver=_resolve_id,
    )


def order_suggestions_by_contributors(
    suggestions: List[Dict[str, Any]],
    contributor_erads_order: List[str],
    key_list: List[str],
    year_field: str = 'nendo',
) -> List[Dict[str, Any]]:
    """Order suggestion wrappers by contributor order + year desc + key priority."""
    return _order_items_by_contributors(
        suggestions,
        contributor_erads_order,
        year_field=year_field,
        key_list=key_list,
        as_suggestions=True,
        id_resolver=None,
    )


def deduplicate_suggestions(
    suggestions: List[Dict[str, Any]],
    mode: str,
    key_order: Optional[List[str]] = None,
    contributor_erads_order: Optional[List[str]] = None,
    year_field: str = 'nendo',
) -> List[Dict[str, Any]]:
    """Sort once, then keep the first item per identity.

    Unified policy for all suggestions:
    - Sort by owner (current user first) -> year desc -> key priority (key_order)
    - Deduplicate by identity, keeping the first appearance

    Identity keys:
    - person: ERAD → normalized name → institution-ja
    - project: kadai_id → japan_grant_number
    """
    if not suggestions:
        return []

    def _person_key(v: Dict[str, Any]) -> str:
        pid = resolve_person_id(v) or ''
        name = (v.get('kenkyusha_shimei_ja_msfullname')
                or v.get('kenkyusha_shimei_en_msfullname')
                or v.get('kenkyusha_shimei')
                or '')
        name_norm = ' '.join((str(name).strip().lower()).split())
        inst_ja = v.get('affiliated-institution-name-ja') or v.get('kenkyukikan_mei_ja') or ''
        inst_ja_norm = ' '.join((str(inst_ja).strip().lower()).split())
        return f'{pid}||{name_norm}||{inst_ja_norm}'

    def _project_key(v: Dict[str, Any]) -> str:
        return resolve_project_id(v)

    pick_key = _person_key if mode == 'person' else _project_key

    # 1) Sort by owner -> year desc -> key priority (shared logic)
    erads = contributor_erads_order or []
    keys = key_order or []
    ordered = order_suggestions_by_contributors(suggestions, erads, keys, year_field=year_field)

    # 2) Keep first item per identity
    seen: Dict[str, Dict[str, Any]] = {}
    result: List[Dict[str, Any]] = []
    for s in ordered:
        v = s.get('value', {})
        sig = pick_key(v)
        if not sig:
            # No identity -> keep as-is
            result.append(s)
            continue
        if sig in seen:
            continue
        seen[sig] = s
        result.append(s)
    return result


def _order_items_by_contributors(
    items: List[Dict[str, Any]],
    contributor_erads_order: List[str],
    *,
    year_field: str = 'nendo',
    key_list: Optional[List[str]] = None,
    as_suggestions: bool = False,
    id_resolver: Optional[Callable[[Dict[str, Any]], Optional[str]]] = None,
) -> List[Dict[str, Any]]:
    """Generic ordering and optional dedup for candidates/suggestions.

    - contributor order: current user first (precomputed), then others
    - within each contributor: year desc
    - key priority: for suggestions, by key_list order (stable otherwise)
    - dedup: if id_resolver provided, keep first occurrence of each ID
    """
    if not items:
        return []

    rank = {erad: i for i, erad in enumerate(contributor_erads_order)}
    missing_rank = len(rank)
    key_priority = {k: i for i, k in enumerate(key_list or [])}

    def owner_rank(it: Dict[str, Any]) -> int:
        v = it.get('value', {}) if as_suggestions else it
        owner = _candidate_owner_erad(v) or ''
        return rank.get(owner, missing_rank)

    def year_rank(it: Dict[str, Any]) -> int:
        v = it.get('value', {}) if as_suggestions else it
        return -_candidate_year(v, year_field)

    def key_prio(it: Dict[str, Any]) -> int:
        if not as_suggestions:
            return 0
        k = it.get('key')
        return key_priority.get(k, len(key_priority))

    # Order by owner -> year (desc) -> key priority
    ordered = sorted(items, key=lambda it: (owner_rank(it), year_rank(it), key_prio(it)))

    if not id_resolver:
        return ordered

    seen = set()
    result: List[Dict[str, Any]] = []
    for it in ordered:
        iid = (id_resolver(it) or '')
        if not iid or iid not in seen:
            result.append(it)
            if iid:
                seen.add(iid)
    return result
