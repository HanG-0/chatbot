## 环境配置

python3.10.x

本项目如果使用线上API，没有环境限制，可以在任意平台运行。如果使用本地模型，建议在**Linux环境下运行**。

建议使用miniconda管理包：**创建虚拟环境后，在项目根目录下运行命令安装包**：

```
pip install -r requirements.txt
```

## 依赖

项目需要后台运行**mysql和redis数据库**。建议使用docker命令直接运行mysql和redis，以下给出的参数可以自行修改。

```dockerfile
# 拉取 MySQL 镜像
docker pull mysql:8.0

# 运行 MySQL 容器
docker run -d \
  --name mysql \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=chatbot \
  -e MYSQL_USER=root \
  -e MYSQL_PASSWORD=root \
  -v mysql_data:/var/lib/mysql \
  --restart unless-stopped \
  mysql:8.0

# 拉取 Redis 镜像
docker pull redis:7.0

# 运行 Redis 容器（无密码）
docker run -d \
  --name redis \
  -p 6379:6379 \
  -v redis_data:/data \
  --restart unless-stopped \
  redis:7.0
```

## 配置文件

项目中的配置文件比较分散。

- 根目录下有.env文件，可以配置minimax和deepseek的api-key，mysql和redis的数据库名称、密码等。
- 模型的具体配置可以参考config文件夹下的model_config.py 可以配置是否使用线上模型，使用什么线上模型，以及所有可用线上模型的api-key。
- 知识库配置，提示词模版配置，状态提示词配置，各项服务的配置（host、端口等），均在config文件夹下。

## 数据库初始化

使用sql文件夹下的SQL脚本即可。



## 需要学习的内容

项目建立在开源框架chatchat的基础上，这是一个提供知识库服务，支持本地/在线模型快速部署的框架，建议详细了解架构，这个框架下又包含以下框架：

- python前端框架：streamlit，本项目前后端不分离。
- vllm：模型推理库，项目运行本地模型，必须使用这个库，但是这个库只能在linux下有比较好的支持
- fastchat：LLM对话框架
- LlamaIndex：知识库构建框架
- langchain：大模型相关应用（智能体）构建框架（内容比较丰富，可以构建知识库，也可以构建聊天机器人）

## 项目启动

启动脚本为startup.py，**支持多种启动参数，在文件中有详细表述**。如果只启动在线模型支持功能，可以使用：

```bash
python startup.py -a --lite
```

## 项目结构

#### 核心启动文件
- **startup.py** - 项目启动脚本，支持多种启动模式（全功能、轻量模式、API模式等）
- **webui.py** - Streamlit Web前端界面入口

#### 工具脚本
- **release.py** - 项目发布脚本
- **shutdown_all.sh** - 关闭所有服务的Shell脚本

#### 功能模块
- **get_predict_result.py** - 获取预测结果的主入口
- **predict_mediate_result.py** - 调解结果预测模块

### configs/ - 配置文件目录

#### 核心配置文件
- **basic_config.py** - 基础配置（日志、临时目录等）
- **model_config.py** - 模型配置（LLM模型、Embedding模型、在线API配置）
- **kb_config.py** - 知识库配置（向量库类型、检索参数、搜索引擎）
- **prompt_config.py** - 提示词模版配置
- **server_config.py** - 服务器配置（端口、地址等）
- **status_prompt.py** - 状态提示词配置

#### 配置示例文件
- **basic_config.py.example** - 基础配置示例
- **model_config.py.example** - 模型配置示例
- **kb_config.py.example** - 知识库配置示例
- **prompt_config.py.example** - 提示词配置示例
- **server_config.py.example** - 服务器配置示例

### server/ - 服务器端核心代码

#### 主要API文件
- **api.py** - 主API服务入口
- **api_allinone_stale.py** - 旧版全功能API
- **llm_api.py** - LLM API服务
- **llm_api_stale.py** - 旧版LLM API
- **llm_api_shutdown.py** - LLM服务关闭工具
- **webui_allinone_stale.py** - 旧版WebUI
- **embeddings_api.py** - Embedding API服务
- **utils.py** - 工具函数集合

#### agent/ - 智能体模块
智能体相关实现，支持复杂任务处理和工具调用

#### callback_handler/ - 回调处理器
处理模型推理过程中的回调事件

#### chat/ - 对话模块
对话逻辑和状态管理

#### db/ - 数据库模块
数据库操作和数据持久化

#### knowledge_base/ - 知识库模块
知识库创建、管理和检索功能

#### memory/ - 记忆模块
对话历史和上下文记忆管理

#### model_workers/ - 模型工作进程
- 各种在线API和本地模型的工作进程实现
- 支持的API：OpenAI、智谱、MiniMax、讯飞星火、百度千帆等

#### reranker/ - 重排序模块
检索结果重排序优化

#### static/ - 静态资源
前端静态文件和资源

---

### webui_pages/ - Web界面页面

#### 主要页面模块
- **dialogue/** - 对话界面
- **knowledge_base/** - 知识库管理界面
- **login/** - 登录界面
- **model_config/** - 模型配置界面
- **record/** - 记录界面
- **signature/** - 签名界面
- **record_out.py** - 记录输出模块

---

### knowledge_base/ - 知识库存储

#### 目录结构
- **samples/** - 示例知识库
- **template_kb/** - 知识库模版
- **test_kb/** - 测试知识库
- **info.db** - 知识库数据库（SQLite）

#### 功能说明
- 存储向量化的文档数据
- 支持FAISS、Milvus等多种向量数据库
- 存储文档元数据和索引信息

---

### document_loaders/ - 文档加载器

#### 加载器实现
- **FilteredCSVloader.py** - 过滤式CSV加载器
- **mypdfloader.py** - 自定义PDF加载器
- **myimgloader.py** - 图片加载器
- **ocr.py** - OCR文字识别模块

#### 功能说明
- 支持多种文档格式加载
- 自定义加载逻辑和过滤规则
- 集成OCR功能处理图片中的文字

---

### embeddings/ - 嵌入模型模块

#### 文件
- **__init__.py** - 模块初始化
- **add_embedding_keywords.py** - 添加嵌入关键词
- **embedding_keywords.txt** - 嵌入关键词文件

#### 功能说明
- Embedding模型管理和调用
- 自定义词汇的嵌入向量
- 支持多种Embedding模型（bge、text2vec等）

---

### model_hub/ - 模型存储中心

#### 目录内容
- **bert-base-chinese/** - BERT中文模型
- **bge-large-zh-v1.5/** - BGE大模型
- **qwen-finetune-v1/** - 微调后的Qwen模型
- **saved_model_threshold_0.5_300_epoch_lr_0.004.pth** - 训练保存的模型权重

#### 功能说明
- 统一存储所有LLM和Embedding模型
- 支持本地模型和HuggingFace模型
- 包含微调后的专用模型

---

### model_predict/ - 模型预测模块

#### 文件
- **__init__.py** - 模块初始化
- **get_predict_result.py** - 获取预测结果
- **predict_mediate_result.py** - 调解结果预测

#### 功能说明
- 调用模型进行推理预测
- 特殊任务预测（如调解结果预测）
- 预测结果处理和格式化

---

### text_splitter/ - 文本分割器

#### 分割器实现
- **__init__.py** - 模块初始化
- **ali_text_splitter.py** - 阿里文本分割器
- **chinese_recursive_text_splitter.py** - 中文递归分割器
- **chinese_text_splitter.py** - 中文文本分割器
- **zh_title_enhance.py** - 中文标题增强

#### 功能说明
- 将长文档分割成合适的文本块
- 支持中文特有的分割规则
- 标题增强提高检索准确度

---

### evaluation/ - 评估模块

#### 目录结构
- **data/** - 原始数据
- **processed_data/** - 处理后的数据
- **说明.md** - 评估说明文档

#### 脚本文件
- **fix_data_format.py** - 修复数据格式
- **generate_test_data.py** - 生成测试数据
- **import_data2base.py** - 导入数据到数据库

#### 功能说明
- 模型性能评估
- 数据集处理和准备
- 评估指标计算

---

### logs/ - 日志文件目录

#### 日志类型
- **controller.log** - 控制器日志
- **openai_api_server.log** - OpenAI API服务日志
- **openai_api.log** - OpenAI API日志
- **model_worker_*.log** - 模型工作进程日志（多个）

#### 功能说明
- 存储所有服务的运行日志
- 日志按日期自动归档
- 便于问题排查和性能分析

---

### contracts/ - 合同文件

#### 目录内容
- **images/** - 合同图片
- **repayment/** - 还款相关文件
- **zhangsan-2026411.pdf** - 示例合同PDF

#### 功能说明
- 存储待处理的合同文档
- 支持多种格式的合同文件
- 用于合同分析和处理的输入数据

---

### docs/ - 文档目录

#### 文档文件
- **诉前调解告知书.md** - 诉前调解告知书模板
- **金融纠纷调解协议书.md** - 金融纠纷调解协议书模板

#### 功能说明
- 存储项目相关文档
- 包含法律文书模板

### sql/ - SQL脚本目录

#### 文件
- **chatbot_init.sql** - 数据库初始化脚本

#### 功能说明
- 数据库表结构定义
- 初始化数据
- 数据库迁移脚本

---

### tests/ - 测试目录

#### 测试模块
- **api/** - API测试
- **custom_splitter/** - 自定义分割器测试
- **document_loader/** - 文档加载器测试
- **kb_vector_db/** - 知识库向量数据库测试
- **samples/** - 测试样本

#### 测试文件
- **test_database_manager.py** - 数据库管理器测试
- **test_migrate.py** - 数据迁移测试
- **test_online_api.py** - 在线API测试

#### 功能说明
- 单元测试和集成测试
- 确保代码质量
- 验证功能正确性

---

### nltk_data/ - NLTK数据目录

#### 目录内容
- **corpora/** - 语料库数据
- **taggers/** - 标注器数据
- **tokenizers/** - 分词器数据

#### 功能说明
- NLTK自然语言处理库的数据
- 支持中文文本处理
- 用于文本预处理和分析

## 总结

### 核心功能模块
1. **对话系统** - 基于LangChain的智能对话
2. **知识库问答** - 向量检索和RAG
3. **多模型支持** - 本地模型和在线API
4. **智能体** - 工具调用和任务执行
5. **Web界面** - Streamlit构建的用户界面

### 技术栈
- **前端**: Streamlit
- **后端**: FastAPI
- **LLM框架**: FastChat, vLLM
- **知识库**: LlamaIndex, LangChain
- **向量数据库**: FAISS, Milvus, pgvector
- **数据库**: SQLite, MySQL, Redis
- **OCR**: PaddleOCR

### 特色功能
- 支持多种大模型（ChatGLM, Qwen, 百川等）
- 灵活的知识库管理
- 强大的文档处理能力
- 智能体工具调用
- 完整的Web管理界面

这个项目是一个功能完善的中文对话机器人系统，适用于各种问答、客服、知识管理等场景。