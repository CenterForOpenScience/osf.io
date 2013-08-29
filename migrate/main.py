import logging

from clean_duplicates import clean
from migrate_data import migrate_all
from resolve_backrefs import resolve_parent_backrefs
from resolve_backrefs import resolve_registration_backrefs
from resolve_backrefs import resolve_fork_backrefs
from resolve_backrefs import rm_null_child_nodes

import generate_links
import diff_links

def main():

    # Delete duplicates: dry run
    clean(dry_run=True, force=True)

    # Prompt to continue
    ok = raw_input('Do you want to delete these records? Enter "continue" to delete: ')
    if ok != 'continue':
        return

    # Delete duplicates for real
    clean(dry_run=False, force=True)

    # Resolve existing database irregularities
    resolve_parent_backrefs()
    resolve_registration_backrefs()
    resolve_fork_backrefs()
    rm_null_child_nodes()

    # Copy data
    migrate_all()

    public_projects = generate_links.generate_projects_urls(public=True)
    logging.warn('Diffing {} public projects...'.format(len(public_projects)))
    diff_links.crawl('public-projects', public_projects)

    private_projects = generate_links.generate_projects_urls(public=False)
    logging.warn('Diffing {} private projects...'.format(len(private_projects)))
    diff_links.crawl('private-projects', private_projects)

    profiles = generate_links.generate_profile_urls()
    logging.warn('Diffing {} profiles...'.format(len(profiles)))
    diff_links.crawl('profiles', profiles)

    static_pages = generate_links.generate_static_urls()
    logging.warn('Diffing {} static pages...'.format(len(static_pages)))
    diff_links.crawl('static-pages', static_pages)

if __name__ == '__main__':
    main()
