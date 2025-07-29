import os
import sys
import json
from typing import List
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ENV import base_url, token,api_key

from visgpt import chat_completion


def extract_requirements(document: str) -> str:
    prompt = f"""
你是专业的需求分析师。

请从以下文档中，提取所有模块名称及对应的需求点 
**需求的定义**：
- 功能需求：描述系统必须执行的功能或服务。例如：用户可以上传图片、支持搜索歌曲、系统自动生成推荐等。
- 非功能需求：描述系统的性能、效率、安全、兼容性等方面的要求。例如：系统在3秒内响应、支持10万并发用户、界面符合公司UI规范等。
- 不要提取以下内容：
  - 背景、市场分析、行业介绍
  - 竞品信息、现状描述
  - UI视觉描述（除非直接体现功能）
  - 流程示意图、参考资料等

要求：
- 按 Markdown 表格输出
- 表头为：序号 | 模块 | 需求点 
- 序号从1开始，每个需求点单独占一行，序号连续递增
- 不要回答多余的文字，只输出表格
- 仔细阅读整个文档，识别出明确表达软件功能、性能、约束等方面要求的语句，并准确对应其在文档中的原文。
- 排除与软件需求无关的信息，如背景介绍、市场分析等。
- 如果文档中没有需求点，请输出“未发现需求点”。

文档如下：{document}
""".strip()

    res = chat_completion(
        base_url=base_url,
        api_key=api_key,
        chat_id="undefined",
        message=prompt,
        detail=True
    )

    return res.get("choices", [{}])[0].get("message", {}).get("content", "【ERROR: 无输出】")


def optimize_requirements(document: str, requirements_md: str) -> str:
    prompt = f"""
你作为资深需求分析师，请严格执行以下任务：

### 任务指令
1. **需求比对分析**（仅在思维中执行）：
   - 逐行比对需求文档与需求表，识别：
     - 【遗漏】文档中明确定义但未在表格中的功能/非功能需求
     - 【冗余】表格中存在但属于以下非需求内容：
       • 背景/市场分析  
       • 竞品对比  
       • UI视觉描述（除非直接关联功能）  
       • 技术实现细节（如"通过集群技术实现"）
     - 【错误】表格中曲解原文或归类错误的需求（如将性能需求误归为可靠性）

2. **表格优化操作**：
   - 增补：为遗漏需求添加新行，序号延续现有表格
   - 删除：完全移除冗余条目
   - 修正：重写错误需求（保持原序号）
   - 归类：确保需求点严格对应模块定义：
     ```markdown
     功能模块 → 系统必须执行的服务（如"支持文件导出"）
     性能需求 → 量化指标（响应时间/并发数等）
     可靠性需求 → 可用性/容错/恢复要求
     其他约束 → 安全/兼容性等
     ```

### 输出规则
- **仅输出**优化后的Markdown表格
- 表格格式：
  | 序号 | 模块 | 需求点 |
  |------|------|--------|
- 序号从1开始连续递增
- 每个需求点必须为文档中**直接引述的原文语句**（可适度精简，禁止改写）
- 模块名称必须与文档章节标题一致

### 强制约束
1. 若未发现任何优化点，直接输出原表
2. 禁止添加解释性文字
3. 禁止合并需求点
4. 非需求内容（如示例中的"例如："）一律忽略

需求文档：
{document}

待优化需求表：
{requirements_md}
""".strip()

    res = chat_completion(
        base_url=base_url,
        api_key=api_key,
        chat_id="undefined",
        message=prompt,
        detail=True
    )

    return res.get("choices", [{}])[0].get("message", {}).get("content", "【ERROR: 无输出】")



 

def final_llm_optimize(md_table: str, max_retries: int = 3, retry_delay: float = 3.0) -> str:
    prompt = f"""
你是一名经验丰富的软件产品分析专家，以下是一张需求表格（Markdown 格式），包含多个模块及其下的多个需求点。

请你对这张表进行**需求点的语义去重与合并**，**模块名必须保持不变**，要求如下：

1. 不要合并模块，保持模块原始命名；
2. 只在同一模块下合并语义重复、描述冗余或表达不同但含义相同的需求点；
3. 每一个需求点单独一行

### 输出规则
- **仅输出**优化后的Markdown表格
- 表格格式：
  | 序号 | 模块 | 需求点 |
  |------|------|--------|
- 序号从1开始连续递增

表格内容如下：
{md_table}
""".strip()

    for attempt in range(1, max_retries + 1):
        try:
            print(f"[info] 尝试调用 LLM 第 {attempt} 次...")
            res = chat_completion(
                base_url=base_url,
                api_key=api_key,
                chat_id="undefined",
                message=prompt,
                detail=True
            )

            # 检查 response 是否为合法内容
            content = res.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if not content or "504" in content or "error" in content.lower():
                raise ValueError("LLM 返回无效或错误内容")

            print("[info] LLM 响应成功 ")
            return content

        except Exception as e:
            print(f"[warn] 第 {attempt} 次调用失败: {e}")
            if attempt < max_retries:
                print(f"[info] 等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                print("[error] 超过最大重试次数，LLM 优化失败 ")
                return "【ERROR: LLM 优化失败，超出最大重试次数】"



 
def main():
    document_path = "D:/2025.7.28-2025.8.4/llm_testcase/data/中烟cutPRD.md"
    with open(document_path, "r", encoding="utf-8") as f:
        prd_content = f.read()

    # 第一步：提取
    extracted = extract_requirements(prd_content)
    with open("output/requirements.md", "w", encoding="utf-8") as f:
        f.write(extracted)
    print("提取完成：requirements.md")

    # 第二步：优化
    optimized = optimize_requirements(prd_content, extracted)
    with open("output/requirements_optimized.md", "w", encoding="utf-8") as f:
        f.write(optimized)
    print("优化完成：requirements_optimized.md")

    # 第三步：模块内去重
    final = final_llm_optimize(optimized)
    with open("output/requirements_final.md", "w", encoding="utf-8") as f:
        f.write(final)
    print("去重完成：requirements_final.md")


if __name__ == "__main__":
    main()
