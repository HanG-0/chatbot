import json
import os
from typing import List, Dict, Any
from datetime import datetime
import sys
sys.path.append(".")

from langchain.docstore.document import Document
from server.knowledge_base.kb_service.faiss_kb_service import FaissKBService
from server.knowledge_base.utils import KnowledgeFile
from server.knowledge_base.kb_service.base import KBServiceFactory

def import_docs_directly(kb_name, docs, filename):
    """
    直接向知识库添加文档

    :param kb_name: 知识库名称
    :param docs: 文档列表，格式为List[Document]
    :param filename: 虚拟文件名，用于标识文档来源
    """
    # 创建Faiss知识库服务实例
    faiss_service = KBServiceFactory.get_service(kb_name,'faiss')

    # 创建KnowledgeFile对象（即使文件不存在，也需要这个对象作为参数）
    kb_file = KnowledgeFile(filename, kb_name)

    # 添加文档（传入kb_file和docs参数）
    result = faiss_service.add_doc(kb_file, docs=docs)

    return result

def parse_chat_records(input_file: str, output_dir: str = "../knowledge_base/template_kb/content"):
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
                    "latter_state": turn.get('latter_state', ''),
                    "AI_reply": turn.get('AI_reply', '')
                }

                # 添加元数据（用于追溯）
                chunk_metadata = {
                    "chunk_id": chunk_id,
                    "conversation_index": conv_idx,
                    "turn_index": hist_idx,
                    "turn_type": "history",
                    "source_file": os.path.basename(input_file)
                }

                all_chunks.append({
                    "content": chunk,
                    "metadata": chunk_metadata
                })
                chunk_id += 1

        # 处理当前对话轮次（如果存在instruction/output）
        if 'instruction' in conversation or 'output' in conversation:
            chunk = {
                "former_state": conversation.get('former_state', ''),
                "customer": conversation.get('instruction', ''),  # instruction作为customer内容
                "latter_state": conversation.get('latter_state', ''),
                "AI_reply": conversation.get('output', '')
            }

            chunk_metadata = {
                "chunk_id": chunk_id,
                "conversation_index": conv_idx,
                "turn_index": -1,  # -1表示这是当前轮次而非history
                "turn_type": "current",
                "source_file": os.path.basename(input_file)
            }

            all_chunks.append({
                "content": chunk,
                "metadata": chunk_metadata
            })
            chunk_id += 1

    # 保存分割后的所有chunks
    filename = f"chunks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file = os.path.join(output_dir, filename)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"✓ 已生成 {len(all_chunks)} 个对话块")
    print(f"✓ 保存至: {output_file}")

    return all_chunks,filename


def prepare_for_vector_db(chunks: List[Dict]):
    """
    准备适合向量数据库导入的格式

    Args:
        chunks: 分割后的chunks列表

    Returns:
        适合update_docs接口的docs参数
    """

    # 构建自定义docs格式
    custom_docs = []

    for chunk_data in chunks:
        chunk_content = chunk_data['content']
        metadata = chunk_data['metadata']

        # 将对话块转换为文本格式（用于向量化）
        text_content = f"""对话状态: {chunk_content['former_state']} → {chunk_content['latter_state']}
用户消息: {chunk_content['customer']}
AI回复: {chunk_content['AI_reply']}"""

        # 创建Document对象（根据你项目中的Document类格式）
        document = Document(page_content=text_content,
                 metadata=metadata)

        custom_docs.append(document)

    return custom_docs


def main():
    """
    主函数：完整的处理流程示例
    """

    # 配置参数
    input_json_file = "data/rag_training_set.json"  # 你的原始聊天记录文件
    kb_name = "template_kb"  # 知识库名称

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
        print(f"状态: {chunk['content']['former_state']} → {chunk['content']['latter_state']}")
        print(f"用户: {chunk['content']['customer'][:100]}...")
        print(f"期望回答: {chunk['content']['ground_truth'][:100]}...")

    # 步骤3: 导入向量数据库
    print("\n" + "=" * 50)
    print("步骤3: 导入向量数据库")
    print("=" * 50)

    # 方式A: 直接使用分割后的chunks导入
    custom_docs = prepare_for_vector_db(chunks)
    import_docs_directly(kb_name, custom_docs, file_name)
    print("导入成功")


if __name__ == "__main__":
    main()