import markdown

from website.settings import \
    PRIVACY_POLICY_PATH, PRIVACY_POLICY_GITHUB_LINK, \
    TERMS_POLICY_PATH, TERMS_POLICY_GITHUB_LINK

def privacy_policy():
    with open(PRIVACY_POLICY_PATH, 'r') as policy_file:
        return {
            'policy_content': markdown.markdown(policy_file.read(), extensions=['toc']),
            'POLICY_GITHUB_LINK': PRIVACY_POLICY_GITHUB_LINK
        }

def terms_policy():
    with open(TERMS_POLICY_PATH, 'r') as policy_file:
        return {
            'policy_content': markdown.markdown(policy_file.read(), extensions=['toc']),
            'POLICY_GITHUB_LINK': TERMS_POLICY_GITHUB_LINK
        }
