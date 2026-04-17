from langchain_openai import ChatOpenAI
# ==============================================================================
# 方案 4： 自定义工作流 Agent (针对特定场景)
# ==============================================================================
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import find_dotenv,load_dotenv
import os

env_file = find_dotenv()
load_dotenv(env_file)


def create_auto_workflow_executor(prompt_template, memory):
    """
    创建简单的对话执行器
    这个执行器会：
    1. 接收用户的一次输入
    2. 使用 LLM 进行简单的对话交互
    3. 返回对话结果
    返回对话结果
    """

    # 如果传入的是字符串，需要转换为 PromptTemplate 对象
    if isinstance(prompt_template, str):
        # 保存原始的已填充提示词
        base_prompt = prompt_template
        
        # 创建新的模板，将用户输入作为变量
        full_template = """用户说：{input}
        {base_prompt}
        """
        
        # 创建 PromptTemplate
        prompt_template = PromptTemplate(
            input_variables=["input", "base_prompt"],
            template=full_template
        )
        
        # 使用 partial 填充 base_prompt 参数
        prompt_template = prompt_template.partial(base_prompt=base_prompt)

    # 创建简单的 LLMChain

    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0.7,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1",
    )

    # 然后创建 LLMChain
    llm_chain = LLMChain(
        llm=llm,
        prompt=prompt_template,
        memory=memory
    )
    # 包装执行器
    class AutoWorkflowExecutor:
        def __init__(self, llm_chain):
            self.llm_chain = llm_chain
            self.workflow_history = []

        async def execute(self, query, callbacks=None):
            """执行对话"""
            print(f"[Chat Start] Query: {query}")

            # 执行 LLM 调用
            result = await self.llm_chain.apredict(input=query, callbacks=callbacks)

            print(f"[Chat Complete] Response: {result}...")

            return result
    return AutoWorkflowExecutor(llm_chain)

