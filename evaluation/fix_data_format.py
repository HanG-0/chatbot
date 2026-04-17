import json
import os
from typing import List, Dict, Any
from datetime import datetime
import sys
sys.path.append(".")

def parse_chat_records(input_file: str, output_dir: str = "./"):
    """
    解析聊天记录并按轮次分割成独立文档

    Args:
        input_file: 原始JSON文件路径
        output_dir: 输出目录
    """

    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 读取原始JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        conversations = json.load(f)

    all_chunks = []
    chunk_id = 0

    for conv_idx, conversation in enumerate(conversations):
        # 处理history中的对话轮次
        if 'history' in conversation and conversation['history']:
            for hist_idx, turn in enumerate(conversation['history']):
                chunk = {
                    "former_state": turn.get('former_state', ''),
                    "customer": turn.get('customer', ''),
                    "expected_state": turn.get('latter_state', ''),
                    "ground_truth": turn.get('AI_reply', '')
                }

                all_chunks.append({
                    "content": chunk,
                })
                chunk_id += 1

        # 处理当前对话轮次（如果存在instruction/output）
        if 'instruction' in conversation or 'output' in conversation:
            chunk = {
                "former_state": conversation.get('former_state', ''),
                "customer": conversation.get('instruction', ''),  # instruction作为customer内容
                "expected_state": conversation.get('expected_state', ''),
                "ground_truth": conversation.get('ground_truth', '')
            }

            all_chunks.append({
                "content": chunk,
            })
            chunk_id += 1

    # 保存分割后的所有chunks
    filename = f"chunks_fixed.json"
    output_file = os.path.join(output_dir, filename)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"✓ 已生成 {len(all_chunks)} 个对话块")
    print(f"✓ 保存至: {output_file}")

    return all_chunks,filename


if __name__ == "__main__":
    # 配置参数
    input_json_file = "data/evaluation_set.json"  # 你的原始聊天记录文件

    # 步骤1: 分割聊天记录
    print("=" * 50)
    print("步骤1: 分割聊天记录")
    print("=" * 50)
    chunks,file_name = parse_chat_records(input_json_file)

    # 步骤2: 预览前3个chunk
    print("\n" + "=" * 50)
    print("步骤2: 预览前3个对话块")
    print("=" * 50)
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n--- Chunk {i+1} ---")
        print(f"状态: {chunk['content']['former_state']} → {chunk['content']['expected_state']}")
        print(f"用户: {chunk['content']['customer'][:100]}...")
        print(f"期望回答: {chunk['content']['ground_truth'][:100]}...")