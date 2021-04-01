def test_item_only_filter(recomm_list, test_list):
    filtered = {}
    test_item_list = {}
    rec_item_list = {}
    for u, i_s in test_list.items():
        i_l = []
        for item in i_s:
            i_l.append(item)
        test_item_list[u] = i_l
    for u, i_s in recomm_list.items():
        i_l = []
        for item in i_s:
            i_l.append(item[0])
        rec_item_list[u] = i_l
    for u, i_s in recomm_list.items():
        new_rec_list = []
        for item in rec_item_list[u]:
            for tup in i_s:
                if item in test_item_list[u] and item == tup[0]:
                    new_rec_list.append((item, tup[1]))
        filtered[u] = new_rec_list

    return filtered
