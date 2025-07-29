import os
import sys
import time
from typing import List
import re
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ENV import base_url, token, api_key
 
from requirements_extration import extract_requirements, optimize_requirements, final_llm_optimize 
 
from visgpt import (   
    create_dataset,
    create_file_collection,
    list_collections,
    chat_completion,
    list_collection_data,
)

def upload_files_and_create_collections(file_list: List[dict], dataset_name="自动需求知识库"):
    print("开始创建知识库...")
    dataset_info = create_dataset(base_url, token, dataset_name, intro="自动上传并提取需求文档")
    print("dataset_info 原始返回:", dataset_info)
    if isinstance(dataset_info, str):
        dataset_id = dataset_info
    elif isinstance(dataset_info, dict):
        dataset_id = dataset_info.get("_id") or dataset_info.get("datasetId")
    else:
        raise ValueError(f"未知返回格式: {dataset_info}")
    print(f"知识库创建成功，ID：{dataset_id}")
    with open("output/dataset_id.txt", "w", encoding="utf-8") as f:
        f.write(dataset_id)


    # 按type分类保存collection_ids
    collections_by_type = {}

    for file_info in file_list:
        ftype = file_info.get("type", "其他")
        print(f"上传文件: {file_info['file_path']} 类型: {ftype} ...")
        try:
            collection_info = create_file_collection(
                base_url=base_url,
                token=token,
                file_path=file_info["file_path"],
                dataset_id=dataset_id,
                training_type="chunk",
                chunk_size=1000
            )
            coll_id = None
            if isinstance(collection_info, dict):
                coll_id = collection_info.get("collectionId")
            elif isinstance(collection_info, str):
                coll_id = collection_info
            if coll_id:
                if ftype not in collections_by_type:
                    collections_by_type[ftype] = []
                collections_by_type[ftype].append(coll_id)
                print(f"创建集合成功，类型: {ftype}，ID: {coll_id}")
            else:
                print(f"未获取到集合ID，返回: {collection_info}")
            time.sleep(1)
        except Exception as e:
            print(f"上传失败: {e}")
            
 # 本地写入集合类型映射
    with open("output/collection_type_map.json", "w", encoding="utf-8") as f:
        json.dump(collections_by_type, f, indent=2, ensure_ascii=False)

    return dataset_id, collections_by_type

def get_all_text_chunks(collection_ids: List[str]) -> List[str]:
    all_chunks = []
    for coll_id in collection_ids:
        print(f"开始读取集合 {coll_id} 的数据块...")
        for _ in range(10):  # 最多重试10次
            try:
                items = list_collection_data(base_url, token, coll_id, page_size=500)

                if items:
                    for item in items:
                        # VisGPT 存在 q/a 字段，但也可能是 text
                        text = item.get("q") or item.get("text") or ""
                        if text.strip():
                            all_chunks.append(text)
                    break  # 成功跳出重试
                else:
                    print(f"集合 {coll_id} 暂无数据，等待 2 秒...")
                    time.sleep(2)
            except Exception as e:
                print(f"获取集合 {coll_id} 数据失败: {e}")
                time.sleep(2)
    print(f"共获取到文本块数量: {len(all_chunks)}")
    return all_chunks


def parse_md_table(md_text):
    """
    解析 Markdown 表格，返回列表(dict)，每条记录包含 '序号', '模块', '需求点'
    假设表头是 | 序号 | 模块 | 需求点 |
    """
    lines = md_text.strip().splitlines()
    data_rows = []
    # 找表头和分隔线的行号
    header_idx = None
    for i, line in enumerate(lines):
        if re.match(r"\|\s*序号\s*\|\s*模块\s*\|\s*需求点\s*\|", line):
            header_idx = i
            break
    if header_idx is None or header_idx+1 >= len(lines):
        print("未找到有效表头，跳过")
        return data_rows
    # 数据行从 header_idx+2 开始
    for line in lines[header_idx+2:]:
        if not line.strip().startswith("|"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 3:
            continue
        data_rows.append({
            "序号": parts[0],
            "模块": parts[1],
            "需求点": parts[2],
        })
    return data_rows


def write_md_table(rows, output_path):
    """
    根据传入的需求列表写出 Markdown 表格
    """
    headers = ["序号", "模块", "需求点"]
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"]*len(headers)) + " |")
    for row in rows:
        line = "| {} | {} | {} |".format(row["序号"], row["模块"], row["需求点"])
        lines.append(line)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"写入合并排序结果: {output_path}")


def merge_and_sort_md_files(md_folder="output", pattern="requirements_chunk_*_optimized.md"):
    import glob

    all_rows = []
    files = sorted(glob.glob(os.path.join(md_folder, pattern)))
    if not files:
        print("未找到任何匹配的Markdown文件")
        return

    print(f"找到 {len(files)} 个文件，开始合并...")

    for file in files:
        print(f"解析文件: {file}")
        with open(file, "r", encoding="utf-8") as f:
            md_text = f.read()
        rows = parse_md_table(md_text)
        all_rows.extend(rows)

    # 按 模块名升序，序号数字升序排序
    def sort_key(row):
        # 序号转int，如果异常设大数放后面
        try:
            idx = int(row["序号"])
        except:
            idx = 999999
        return (row["模块"], idx)

    all_rows.sort(key=sort_key)

    # 重新赋序号，从1开始
    for i, row in enumerate(all_rows, 1):
        row["序号"] = str(i)

    # 写回文件
    write_md_table(all_rows, os.path.join(md_folder, "final_merged_sorted_requirements.md"))

import re
from collections import defaultdict

def split_markdown_by_module(md_table: str) -> dict:
    """
    将完整 Markdown 表格按模块拆分为 {模块名: 子表格markdown字符串}
    """
    lines = md_table.strip().splitlines()
    if len(lines) < 3:
        return {}

    header = lines[:2]  # 表头两行
    body = lines[2:]

    module_rows = defaultdict(list)

    for line in body:
        parts = [col.strip() for col in line.strip().split("|")[1:-1]]  # 排除最外的空列
        if len(parts) != 3:
            continue
        _, module, requirement = parts
        module_rows[module].append(line)

    result = {}
    for module, rows in module_rows.items():
        module_table = "\n".join(header + rows)
        result[module] = module_table

    return result

def optimize_per_module_and_merge(md_table: str) -> str:
    """
    拆分 -> 每模块优化 -> 合并为总表格，重新编号
    """
    module_tables = split_markdown_by_module(md_table)

    all_rows = []
    index = 1
    for module, table in module_tables.items():
        print(f"[info] 正在优化模块：{module}")
        optimized_md = final_llm_optimize(table)

        lines = optimized_md.strip().splitlines()
        if len(lines) < 3:
            continue

        for line in lines[2:]:  # 跳过表头
            parts = [col.strip() for col in line.strip().split("|")[1:-1]]
            if len(parts) != 3:
                continue
            # 替换序号为新的全局编号
            parts[0] = str(index)
            index += 1
            all_rows.append(f"| {' | '.join(parts)} |")

    final_md = "| 序号 | 模块 | 需求点 |\n|------|------|--------|\n" + "\n".join(all_rows)
    return final_md

def filter_separator_lines(md_text: str) -> str:
    """
    去除类似 | 165 | ---------- | .... | 的分割线样式的行
    """
    lines = md_text.splitlines()
    filtered_lines = []
    for line in lines:
        if re.match(r"^\|\s*\d+\s*\|\s*-+\s*\|.*\|$", line):
            continue
        filtered_lines.append(line)
    return "\n".join(filtered_lines)



def requirement_main():
    # 你的待上传文件列表
    file_list = [
        {
            "file_path": "D:\\2025.7.14-2025.7.20\\llm_testcase\\data\\需求文件\\需求分析报告-湖北中烟新型烟草产品调研与开发信息反馈系统项目.docx",
            "type": "需求文档"
        },
        {
            "file_path": "D:\\2025.7.14-2025.7.20\\llm_testcase\\data\\需求文件\\湖北中烟工程中心数字管理应用用户操作手册v1.0.docx",
            "type": "用户手册"
        },
        {
            "file_path": "D:\\2025.7.14-2025.7.20\\llm_testcase\\data\\需求文件\\数字信息化管理应用系统接口文档.docx",
            "type": "技术文档"
        }
    ]

    os.makedirs("output", exist_ok=True)

    #  1. 创建知识库并上传文件创建集合
    dataset_id, collections_by_type = upload_files_and_create_collections(file_list)

    demand_collections = collections_by_type.get("需求文档", [])

    chunks = get_all_text_chunks(demand_collections)


    optimized_md_tables = []

    for i, chunk_text in enumerate(chunks, start=1):
        print(f"\n=== 处理第 {i} 个文本块 ===")

        md_extracted = extract_requirements(chunk_text)
        if not md_extracted or "未发现需求点" in md_extracted:
            print(f"第 {i} 个文本块无提取结果，跳过")
            continue

        md_optimized = optimize_requirements(chunk_text, md_extracted)
        if not md_optimized or "未发现需求点" in md_optimized:
            print(f"第 {i} 个文本块优化失败，使用提取结果")
            md_optimized = md_extracted

        chunk_file = f"output/requirements_chunk_{i}_optimized.md"
        with open(chunk_file, "w", encoding="utf-8") as f:
            f.write(md_optimized)
        print(f"已保存优化结果到: {chunk_file}")

        optimized_md_tables.append(md_optimized)
        time.sleep(1)

    merge_and_sort_md_files()

    with open("output/final_merged_sorted_requirements.md", "r", encoding="utf-8") as f:
        merged_md = f.read()

    final_result = optimize_per_module_and_merge(merged_md)

    final_result = filter_separator_lines(final_result)

    with open("output/final_requirements.md", "w", encoding="utf-8") as f:
        f.write(final_result)
        
    print(f"最终需求提取与优化完成，结果保存在: {final_result}")
    print(final_result)

    

if __name__ == "__main__":
    requirement_main()
