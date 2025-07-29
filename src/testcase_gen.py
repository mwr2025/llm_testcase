import os
import sys
import concurrent.futures
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from visgpt import chat_completion
from ENV import base_url, api_key
from requirement import split_markdown_by_module,upload_files_and_create_collections
from test import get_manual_and_api_collection_ids_from_local

def extract_manual_and_api_collections(collections_by_type: dict) -> list:
    """
    从 collections_by_type 中提取类型为“用户手册”和“接口文档”的所有合集 ID。
    """
    target_types = ["用户手册", "接口文档"]
    extracted_ids = []

    for doc_type in target_types:
        ids = collections_by_type.get(doc_type, [])
        if ids:
            print(f"{doc_type} 类型集合 ID 数量: {len(ids)}")
            extracted_ids.extend(ids)
        else:
            print(f"未找到类型为 {doc_type} 的集合")

    return extracted_ids

def generate_test_case_for_module(module: str, table: str, dataset_id: str, collection_ids: list) -> list:
    """
    处理单个模块的测试用例生成，返回列表形式的 Markdown 表格 body 行（不含表头）
    """
    prompt = f"""
你是专业的软件测试工程师，请根据下方模块的需求点生成系统测试用例。

### 输入格式：
{table}

### 输出要求：
- 表格字段依次为：
  | 序号 | 模块名称 | 需求点 | 用例测试点 | 前提与约束 | 操作步骤及输入数据 | 预期结果 |
- 每条需求点应对应至少 1 个测试用例（若可细化则多个）；
- 所有内容尽量结合上下文，不要虚构系统不存在的功能；
- 如果需求点模糊难测，请用合理前提约束进行假设；
- 输出纯 Markdown 表格，不要输出多余文字。
""".strip()

    res = chat_completion(
        base_url=base_url,
        api_key=api_key,
        chat_id="test-case-gen",
        message=prompt,
        detail=True,
        dataset_ids=[dataset_id],
        collection_ids=collection_ids, # 使用 dataset_id 作为集合 ID
    )

    content = res.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content or "error" in content.lower():
        print(f"[warn] 模块 {module} 测试用例生成失败，跳过")
        return []

    lines = content.strip().splitlines()
    if len(lines) < 3:
        return []

    body_lines = lines[2:]
    return body_lines


def generate_test_cases(md_table: str, dataset_id: str, collection_ids: list) -> str:
    """
    多线程并发生成测试用例，按模块划分 → 合并 → 输出总表格
    """
    module_tables = split_markdown_by_module(md_table)
    print(f"[info] 共拆分出 {len(module_tables)} 个模块，开始并发生成测试用例...")

    all_body_lines = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_module = {
        executor.submit(generate_test_case_for_module, module, table, dataset_id, collection_ids): module
        for module, table in module_tables.items()
        }

        for future in concurrent.futures.as_completed(future_to_module):
            module = future_to_module[future]
            try:
                result = future.result()
                if result:
                    print(f"[ok] 模块 {module} 生成 {len(result)} 条测试用例")
                    all_body_lines.extend(result)
                else:
                    print(f"[warn] 模块 {module} 未生成有效测试用例")
            except Exception as e:
                print(f"[error] 模块 {module} 处理异常: {e}")

    if not all_body_lines:
        return "未生成任何测试用例"

    # 重写序号为全局编号
    final_rows = []
    index = 1
    for line in all_body_lines:
        parts = [col.strip() for col in line.strip().split("|")[1:-1]]
        if len(parts) != 7:
            continue
        parts[0] = str(index)
        index += 1
        final_rows.append("| " + " | ".join(parts) + " |")

    final_table = (
        "| 序号 | 模块名称 | 需求点 | 用例测试点 | 前提与约束 | 操作步骤及输入数据 | 预期结果 |\n"
        "|------|----------|--------|------------|------------|--------------------|----------|\n"
        + "\n".join(final_rows)
    )

    return final_table


def testcase_main():
    dataset_id_path = "D:/2025.7.28-2025.8.4/llm_testcase/src/output/dataset_id.txt"
    requirements_path = "D:/2025.7.28-2025.8.4/llm_testcase/src/output/final_requirements.md"
    output_path = "D:/2025.7.28-2025.8.4/llm_testcase/src/output/final_testcases.md"

    if not os.path.exists(dataset_id_path) or not os.path.exists(requirements_path):
        print("缺少必要文件（dataset_id.txt 或 final_requirements.md）")
        return

    with open(dataset_id_path, "r", encoding="utf-8") as f:
        dataset_id = f.read().strip()

    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements_md = f.read()
    
    collections_by_type_path = "D:/2025.7.28-2025.8.4/llm_testcase/output/collection_type_map.json"
    if not os.path.exists(collections_by_type_path):
        print("缺少集合类型映射文件 collection_type_map.json")
        return

    selected_collections = get_manual_and_api_collection_ids_from_local()
    all_ids = selected_collections.get("用户手册", []) + selected_collections.get("技术文档", [])

    print("开始生成测试用例...")
    final_testcases = generate_test_cases(requirements_md, dataset_id, all_ids)

    os.makedirs("output", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_testcases)

    print(f"测试用例生成完成，保存在：{output_path}")


if __name__ == "__main__":
    testcase_main()
