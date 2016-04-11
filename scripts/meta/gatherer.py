import requests
import json
from website.settings import GITHUB_API_TOKEN

the_filename = 'website/static/git_logs.json'


def gather_pr_data():
    pr_data = []
    auth_header = {'Authorization': 'token %s' % GITHUB_API_TOKEN}
    res = requests.get('https://api.github.com/repos/centerforopenscience/osf.io/pulls?state=closed&per_page=100',
                       headers=auth_header)

    while len(pr_data)<100:
        if res.status_code == 200:
            for item in res.json():
                try:
                    sha = item['merge_commit_sha']
                except TypeError:
                    sha = None
                if sha:
                    pr_data.append(item)
            try:
                next_link = res.links['next']
            except KeyError:
                break
            res = requests.get(next_link['url'])
        else:
            break

    return pr_data


def main():
    if GITHUB_API_TOKEN:
        pr_data = json.dumps(gather_pr_data())
        with open(the_filename, 'w') as f:
            f.write(pr_data)

if __name__ == '__main__':
    main()

