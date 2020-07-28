from function import *

new_dict = {"生田輝": [
    "来点生田輝",
    "来点生田辉",
    "来点辉哥哥",
    "来点teru"
]}

group_list = load_group_list()
for g_id in group_list:
    print("updating {}".format(g_id))
    group_keyword = json.loads(r.hget("KEYWORDS", g_id))
    group_keyword.update(new_dict)
    r.hset("KEYWORDS", g_id, json.dumps(group_keyword, ensure_ascii=False))
    
