from function import *

new_dict = {"高野麻里佳": [
    "来点高野麻里佳"
]}

group_list = load_group_list()
for g_id in group_list:
    print("updating {}".format(g_id))
    init_keyword_list(g_id)
    group_keyword = json.loads(r.get("key_{}".format(g_id)))
    group_keyword.update(new_dict)
    update_database("KEYWORDS", g_id, json.dumps(group_keyword, ensure_ascii=False))
    init_keyword_list(g_id)