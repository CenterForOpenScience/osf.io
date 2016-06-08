import json
import os
import requests
import re
from website.settings import GITHUB_API_TOKEN
from subprocess import check_output

GIT_LOGS_FILE = os.path.join('website', 'static', 'built', 'git_logs.json')
GIT_STATUS_FILE = os.path.join('website', 'static', 'built', 'git_branch.txt')


def gather_pr_data(current_branch='develop', master_branch='master'):
    regex = re.compile(ur'\(#([\d]{4,})\)|Merge pull request #([\d]{4,})')
    pr_data = []
    headers = {
        'Authorization': 'token %s' % GITHUB_API_TOKEN,
        'media_type': 'application/vnd.github.VERSION.sha',
    }
    # GET /repos/:owner/:repo/compare/hubot:branchname...octocat:branchname
    url_string = 'https://api.github.com/repos/centerforopenscience/osf.io/compare/{}...{}'
    url = url_string.format(master_branch, current_branch)
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        commits = data['commits']
        if commits:
            commits.reverse()
        index = 0
        for item in commits:
            index += 1
            commit_message = item['commit']['message']
            found_list = re.findall(regex, commit_message)
            if found_list:
                pr_one, pr_two = found_list[0]
                pr = int(pr_one or pr_two)
                pr_data.append(get_pr_data(pr))
    return pr_data


def get_pr_data(pr):
    headers = {
        'Authorization': 'token %s' % GITHUB_API_TOKEN,
        'media_type': 'application/vnd.github.VERSION.sha',
    }
    # GET /repos/:owner/:repo/pulls/:number
    res = requests.get('https://api.github.com/repos/centerforopenscience/osf.io/pulls/{}'.format(pr),
                       headers=headers)
    if res.status_code == 200:
        return res.json()
    else:
        return {}


def main():
    current_branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).rstrip()
    with open(GIT_STATUS_FILE, 'w') as f:
        f.write(current_branch)
    if GITHUB_API_TOKEN:
        pr_data = json.dumps(gather_pr_data(current_branch))
        with open(GIT_LOGS_FILE, 'w') as f:
            f.write(pr_data)

if __name__ == '__main__':
    main()
