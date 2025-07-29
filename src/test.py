from typing import List, Dict
from visgpt import list_collection_data
import os
import json

base_url="https://zy.dwz.ink:15500"
token="visgpt-37QhkR79wqO5XkQTyDypg60OM6ryOeH5qpLeImB5fHKanqyn84eBIJ5fTROb"
api_key="visgpt-rdalvuH29RvwHMwlpoNETVfTRt6305dlGVrgndzb1VCse1Mg14zEWWgHfbF"
def get_manual_and_api_collection_ids_from_local() -> Dict[str, List[str]]:
    """
    从本地 JSON 文件中读取 '用户手册' 和 '接口文档' 的集合 ID 列表。
    """
    path = "output/collection_type_map.json"
    if not os.path.exists(path):
        print(f"[错误] 文件不存在: {path}")
        return {}

    with open(path, "r", encoding="utf-8") as f:
        collections_by_type = json.load(f)

    manual_ids = collections_by_type.get("用户手册", [])
    api_doc_ids = collections_by_type.get("技术文档", [])

    print("用户手册集合 ID:", manual_ids)
    print("技术文档集合 ID:", api_doc_ids)

    return {
        "用户手册": manual_ids,
        "技术文档": api_doc_ids
    }

if __name__ == "__main__":
    selected_collections = get_manual_and_api_collection_ids_from_local()
    all_ids = selected_collections.get("用户手册", []) + selected_collections.get("技术文档", [])
    print("最终处理的合集 ID:", all_ids)
