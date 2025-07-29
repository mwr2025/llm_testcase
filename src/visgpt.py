import os
import sys
import requests
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ENV import base_url, token

# 通用 方法
def call_get_api(url: str, token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result.get("code") == 200:
            return result.get("data", {})
        else:
            raise Exception(f"API Error: {result.get('message', 'Unknown error')}")
    else:
        raise Exception(f"HTTP Error {response.status_code}: {response.text}")

def call_post_api(url: str, token: str, payload: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result.get("code") == 200:
            return result.get("data", {})
        else:
            raise Exception(f"API Error: {result.get('message', 'Unknown error')}")
    else:
        raise Exception(f"HTTP Error {response.status_code}: {response.text}")

def call_delete_api(url: str, token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Content-Type": "application/json"
    }
    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result.get("code") == 200:
            return result.get("data", {})  # 一般是 null
        else:
            raise Exception(f"API Error: {result.get('message', 'Unknown error')}")
    else:
        raise Exception(f"HTTP Error {response.status_code}: {response.text}")


# 创建知识库
def create_dataset(base_url: str, token: str, name: str, intro: str = "", avatar: str = "/icon/logo.svg",
                   vector_model: str = "bge-large-zh-v1.5", agent_model: str = "chatglm3-6b",
                   parent_id: str = None) -> str:
    url = f"{base_url}/api/core/dataset/create"
    payload = {
        "parentId": parent_id,
        "type": "dataset",
        "name": name,
        "intro": intro,
        "avatar": avatar,
        "vectorModel": vector_model,
        "agentModel": agent_model
    }
    return call_post_api(url, token, payload)

# 修改知识库名称和介绍
def update_dataset(base_url: str, token: str, dataset_id: str, name: str, intro: str) -> bool:
    url = f"{base_url}/api/core/dataset/update"
    payload = {
        "id": dataset_id,
        "name": name,
        "intro": intro
    }
    call_post_api(url, token, payload)
    return True

# 获取知识库列表
def get_datasets(base_url: str, token: str) -> list:
    url = f"{base_url}/api/core/dataset/list"
    return call_get_api(url, token)

# 获取知识库详情
def get_dataset_details(base_url: str, token: str, dataset_id: str) -> dict:
    url = f"{base_url}/api/core/dataset/detail?id={dataset_id}"
    return call_get_api(url, token)

# 删除一个知识库
def delete_dataset(base_url: str, token: str, dataset_id: str) -> bool:
    url = f"{base_url}/api/core/dataset/delete?id={dataset_id}"
    call_delete_api(url, token)
    return True

# 创建一个文件集合
def create_file_collection(base_url: str, token: str, file_path: str, dataset_id: str, 
                           training_type: str = "chunk", chunk_size: int ="", 
                           chunk_splitter: str = "", qa_prompt: str = "") -> dict:
    """
    上传本地文件到指定知识库并创建集合

    :param base_url: 上传接口基础URL（例如 https://guyan.zzux.com:15500）
    :param token: 授权Token
    :param file_path: 本地文件路径
    :param dataset_id: 目标知识库ID
    :param training_type: 分割模式（chunk / qa）
    :param chunk_size: 每个chunk长度
    :param chunk_splitter: 自定义分隔符（可选）
    :param qa_prompt: 自定义QA提示词（可选）
    :return: 返回集合ID等信息
    """

    url = f"{base_url}/api/core/dataset/collection/create/localFile"

    headers = {
        "Authorization": f"Bearer {token.strip()}"
    }

    data_dict = {
        "datasetId": dataset_id,
        "parentId": "",
        "trainingType": training_type,
        "chunkSize": chunk_size,
        "chunkSplitter": chunk_splitter,
        "qaPrompt": qa_prompt,
        "metadata": {}
    }

    files = {
        "file": open(file_path, "rb"),
        "data": (None, json.dumps(data_dict), "application/json")
    }

    response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        result = response.json()
        if result.get("code") == 200:
            return result["data"]
        else:
            raise Exception(f"API Error: {result.get('message', 'Unknown error')}")
    else:
        raise Exception(f"HTTP Error {response.status_code}: {response.text}")

# 创建纯文本集合
def create_text_collection_with_common_api( base_url: str,token: str,text: str,dataset_id: str,
                                            name: str,training_type: str,chunk_size: int = 8000,
                                            parent_id: str = None,chunk_splitter: str = "",
                                            qa_prompt: str = "",metadata: dict = None,
):
    if metadata is None:
        metadata = {}

    url = f"{base_url}/api/core/dataset/collection/create/text"
    payload = {
        "text": text,
        "datasetId": dataset_id,
        "parentId": parent_id,
        "name": name,
        "trainingType": training_type,
        "chunkSize": chunk_size,
        "chunkSplitter": chunk_splitter,
        "qaPrompt": qa_prompt,
        "metadata": metadata,
    }

    return call_post_api(url, token, payload)

# 获取集合列表
def list_collections(base_url, token, dataset_id):
    url = f"{base_url}/api/core/dataset/collection/list"
    payload = {
        "pageNum": 1,
        "pageSize": 10,
        "datasetId": dataset_id,
        "collectionId": "",
        "parentId": None,
        "searchText": ""
    }
    return call_post_api(url, token, payload)

# 获取集合详情
def get_collection_detail(base_url, token, collection_id):
    url = f"{base_url}/api/core/dataset/collection/detail?id={collection_id}"
    return call_get_api(url, token)

# 获取集合详情
def get_collection_detail(base_url, token, collection_id):
    url = f"{base_url}/api/core/dataset/collection/detail?id={collection_id}"
    return call_get_api(url, token)


# 删除集合
def delete_collection(base_url, token, collection_id):
    url = f"{base_url}/api/core/dataset/collection/delete?id={collection_id}"
    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Content-Type": "application/json"
    }
    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result.get("code") == 200:
            return {"success": True}
        else:
            raise Exception(f"API Error: {result.get('message', 'Unknown error')}")
    else:
        raise Exception(f"HTTP Error {response.status_code}: {response.text}")
    
# 获取集合数据列表
def list_collection_data(base_url, token, collection_id, page_size=500) -> list:
    url = f"{base_url}/api/core/dataset/data/list"
    payload = {
        "pageNum": 1,
        "pageSize": page_size,
        "collectionId": collection_id,
        "searchText": ""
    }
    raw = call_post_api(url, token, payload)

    # ✅ 正确路径：data 是列表
    if isinstance(raw.get("data"), list):
        return raw["data"]
    else:
        print("[warn] 返回数据结构异常:", raw)
        return []


 
# 搜索测试
# 此函数用于在指定知识库中进行文本搜索，支持多种参数配置。
def search_test(
    base_url: str,
    api_key: str,
    dataset_id: str,
    text: str,
    limit: int = 5000,
    similarity: float = 0.6,
    search_mode: str = "embedding",
    using_rerank: bool = False,
    extension_query: bool = False,
    extension_model: str = "",
    extension_bg: str = ""
):
    url = f"{base_url}/api/core/dataset/searchTest"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "datasetId": dataset_id,
        "text": text,
        "limit": limit,
        "similarity": similarity,
        "searchMode": search_mode,
        "usingReRank": using_rerank
    }

    # 可选参数
    if extension_query:
        payload["datasetSearchUsingExtensionQuery"] = extension_query
    if extension_model:
        payload["datasetSearchExtensionModel"] = extension_model
    if extension_bg:
        payload["datasetSearchExtensionBg"] = extension_bg

    response = requests.post(url, headers=headers, json=payload)
    return response.json()



# 聊天接口
# 该函数用于与聊天模型进行交互，支持多种参数配置。
def chat_completion(
    base_url: str,
    api_key: str,
    chat_id: str,
    message: str,
    stream: bool = False,
    detail: bool = True,
    dataset_ids: list = None,
    collection_ids: list = None,
    variables: dict = None
):
    import requests
    import json

    url = f"{base_url}/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "chatId": chat_id,
        "stream": stream,
        "detail": detail,
        "messages": [
            {
                "content": message,
                "role": "user"
            }
        ]
    }

    if dataset_ids:
        payload["datasetIds"] = dataset_ids
    if collection_ids:
        payload["collectionIds"] = collection_ids
    if variables:
        payload["variables"] = variables

    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"[debug] 状态码: {response.status_code}")
        print(f"[debug] 返回内容预览: {response.text[:200]}")  # 避免输出太多

        if response.status_code != 200:
            return {"error": f"请求失败，状态码: {response.status_code}", "response": response.text}

        return response.json()
    except Exception as e:
        return {"error": f"请求异常: {e}"}

 

   

# 示例运行
if __name__ == "__main__":
    # #创建
    # dataset_id = create_dataset(
    #     base_url=base_url,
    #     token=token,
    #     name="测试知识库",
    #     intro="测试用例自动生成相关文档"
    # )
    # print("成功创建知识库，ID:", dataset_id)

    # #更新
    # update_dataset(
    #     base_url=base_url,
    #     token=token,
    #     dataset_id="68804191016c31b1f35fe348",
    #     name="测试用例自动生成知识库",
    #     intro="测试文档用户手册等相关文档"
    # )
    # print("成功更新知识库名称和介绍")

    # # 获取列表
    # datasets = get_datasets(base_url=base_url, token=token)
    # print("成功获取知识库列表")
    # for ds in datasets:
    #     print(f"ID: {ds['_id']}, Name: {ds['name']}, Intro: {ds['intro']}")

    # #获取详情
    # dataset_id = "68804191016c31b1f35fe348" 
    # details = get_dataset_details(base_url=base_url, token=token, dataset_id=dataset_id)
    # print("成功获取知识库详情")
    # print("知识库详情:", details)

    # # 删除知识库
    # dataset_id = "68808be0016c31b1f3664e61"   
    # success = delete_dataset(base_url, token, dataset_id)
    # if success:
    #     print(f"成功删除知识库：{dataset_id}")
    
    # # 创建一个文件集合
    # base_url = base_url
    # token = token
    # dataset_id = "68804191016c31b1f35fe348"
    # file_path = "D:\\2025.7.14-2025.7.20\\相关技术描述.docx"
    # chunk_size = 1024

    # result = create_file_collection(base_url, token, file_path, dataset_id, chunk_size=chunk_size)
    # print("创建集合成功，集合ID:", result["collectionId"])
    # print("插入结果:", result)

    # # 创建纯文本集合
    # text="这里是要上传的文本内容"
    # dataset_id = "68804191016c31b1f35fe348"
    # name="测试训练"
    # chunk_size = 1024
    # data = create_text_collection_with_common_api(base_url,token,text=text,dataset_id=dataset_id,
    #                                               name=name,training_type="qa",chunk_size=chunk_size,
    #     )
    # print("创建集合成功，集合ID:", data.get("collectionId"))
    # print("插入结果:", data.get("results"))

    # # 获取集合列表
    # dataset_id = "68804191016c31b1f35fe348"  # 替换为实际的知识库ID
    # collection_list = list_collections(base_url, token, dataset_id)
    # print("集合总数:", collection_list.get("total"))

    # 获取集合详情
    collection_id = "68882c436ec715b77077dd45"  
    detail = get_collection_detail(base_url, token, collection_id)
    print("集合名称:", detail )

    # # 获取集合数据
    # collection_id = "6880946e016c31b1f3674b01" 
    # data_list = list_collection_data(base_url, token, collection_id)
    # print("数据条数:", data_list)

    # # 删除集合
    # collection_id = "6880946e016c31b1f3674b01" 
    # deleted = delete_collection(base_url, token, collection_id)
    # print("删除成功:", deleted["success"])

    # # 搜索测试调用
    # search_result = search_test(
    #     base_url,
    #     api_key="visgpt-rdalvuH29RvwHMwlpoNETVfTRt6305dlGVrgndzb1VCse1Mg14zEWWgHfbF",
    #     dataset_id="68804191016c31b1f35fe348",
    #     text="会员管理"
    # )
    # print("搜索结果:", search_result)

    # 发起对话调用
    chat_result = chat_completion(
        base_url=base_url,
        api_key="visgpt-rdalvuH29RvwHMwlpoNETVfTRt6305dlGVrgndzb1VCse1Mg14zEWWgHfbF",
        chat_id="undefined",
        dataset_ids=["68804191016c31b1f35fe348"],
        message="会员管理的功能",
        variables={"uid": "asdfadsfasfd2323", "name": "张三"}
    )
     