import re
# import time
from collections import Counter
from concurrent.futures import (ProcessPoolExecutor, as_completed,
                                ThreadPoolExecutor)
from urllib.parse import urlparse
import plotly.graph_objects as go
import requests

OWNER = "Netflix"
TOKEN = "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"
PATTERN = re.compile('\<(.*?)\>')
commit_query = "https://api.github.com/repos/{}/{}/commits?per_page=100&page={}"


def count_commits(query_url):
    repo_counter = Counter()
    r = requests.get(query_url, headers={"Authorization": f"token {TOKEN}"})
    for commit in r.json():
        commit = commit["commit"]
        if not commit["message"].startswith("Merge pull request #"):
            author = commit["author"]["email"]
            repo_counter[author] += 1
    return repo_counter


def count_repo(repo):
    commit_request = requests.get(commit_query.format(OWNER, repo, 1),
                                  headers={"Authorization": f"token {TOKEN}"})
    commit_headers = commit_request.headers
    if "Link" not in commit_headers:
        repo_counter = Counter()
        for commit in commit_request.json():
            if "commit" not in commit:
                break
            commit = commit["commit"]
            if not commit["message"].startswith("Merge pull request #"):
                author = commit["author"]["email"]
                repo_counter[author] += 1
        return repo_counter
    else:
        last_commit_page = re.findall(PATTERN, commit_headers['Link'])[1]
        commit_pages_nb = int(urlparse(last_commit_page).query.split('=')[-1])
        commit_tasks = []
        c = Counter()
        with ThreadPoolExecutor(max_workers=16) as tpe:
            for i in range(1, commit_pages_nb + 1):
                q = commit_query.format(OWNER, repo, i)
                commit_tasks.append(tpe.submit(count_commits, q))
            for commit_task in as_completed(commit_tasks):
                c += commit_task.result()
        return c


def get_repo_list():
    query = "https://api.github.com/users/{}/repos?page={}"
    r = requests.get(query.format(OWNER, 1), headers={
        "Authorization": f"token {TOKEN}"})
    repositories = []
    headers = r.headers

    last_page = re.findall(PATTERN, headers['Link'])[1]
    pages_nb = int(urlparse(last_page).query.split('=')[1])
    for i in range(1, pages_nb + 1):
        q = query.format(OWNER, i)
        r = requests.get(q, headers={"Authorization": f"token {TOKEN}"})
        for repo in r.json():
            repositories.append(repo["name"])
            # print(repo["name"])
    return repositories


def get_stats():
    commits_number = sum(authors.values())
    top100_commit_values = [val for name, val in top100]
    top100_commit_sum = sum(top100_commit_values)
    names = [name for name, val in top100]
    names.append('other')
    top100_commit_values.append(commits_number - top100_commit_sum)
    fig = go.Figure(data=[go.Pie(labels=names,
                                 title=f"TOP-100 committers in {OWNER}",
                                 values=top100_commit_values,
                                 showlegend=False, textinfo="none")])
    fig.show()


if __name__ == '__main__':
    # start = time.time()
    authors = Counter()
    tasks = []
    with ProcessPoolExecutor(max_workers=16) as ppe:
        for repository in get_repo_list():
            tasks.append(ppe.submit(count_repo, repository))

        for task in as_completed(tasks):
            authors += task.result()
    top100 = authors.most_common(100)
    print(dict(top100))
    # end = time.time()
    # print(end - start)
    get_stats()
