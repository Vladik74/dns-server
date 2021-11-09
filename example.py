from collections import Counter
import plotly.graph_objects as go


def get_stats():
    commits_number = sum(authors.values())
    top100_commit_values = [val for name, val in top100]
    top100_commit_sum = sum(top100_commit_values)
    names = [name for name, val in top100]
    names.append('other')
    top100_commit_values.append(commits_number - top100_commit_sum)
    fig = go.Figure(data=[go.Pie(labels=names, values=top100_commit_values)])
    fig.show()


    print(*names)
    print(*top100_commit_values)



authors = Counter()
authors['aaa'] = 3
authors['bbbb'] = 4
authors['cccccc'] = 6
top100 = authors.most_common(100)
get_stats()
