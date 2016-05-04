def get_sorted_index(l, reverse=True):
    return sorted(range(len(l)), key=lambda k: l[k], reverse=reverse)
