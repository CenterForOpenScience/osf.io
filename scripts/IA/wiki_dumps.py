import os
import math
import asyncio
import requests
import argparse

API_URL = 'http://localhost:8000'
HERE = os.path.dirname(os.path.abspath(__file__))


async def get_wiki_pages(guid, page, result={}):
    url = f'{API_URL}/v2/registrations/{guid}/wikis/?page={page}'
    result[page] = requests.get(url).json()['data']
    return result


async def write_wiki_content(page):
    with open(os.path.join(HERE, f'{page["attributes"]["name"]}.md'), 'wb') as fp:
        fp.write(requests.get(page['links']['download']).content)


async def main(guid):
    """
    Usually asynchronous requests/writes are reserved for times when it's truely necessary, but given the fact
    that we have like 4 days left in the sprint and this going to be the first py3 thing in the repo, I've decided to
    whip out the big guns and concurrently gather all wiki pages simultaneously (except for the first one) and then
    stream them all to local files simultaneously just because it's easy to do with py3 and will save a nano-second or
    two.

    :param guid:
    :return:
    """

    url = f'{API_URL}/v2/registrations/{guid}/wikis/'

    data = requests.get(url).json()
    pages = math.ceil(int(data['links']['meta']['total']) / int(data['links']['meta']['per_page']))
    result = {1: data['data']}
    tasks = []

    for i in range(1, pages):
        task = get_wiki_pages(guid, i + 1, result)
        tasks.append(task)

    await asyncio.gather(*tasks)

    pages_as_list = []
    # through the magic of async all our pages have loaded.
    for page in list(result.values()):
        pages_as_list += page

    print(len(pages_as_list))

    write_tasks = []
    for page in pages_as_list:
        write_tasks.append(write_wiki_content(page))

    await asyncio.gather(*write_tasks)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-id', '--guid', help='The guid of the registration if who\'s wiki you want to dump.')
    args = parser.parse_args()

    guid = args.guid
    asyncio.run(main(guid))
