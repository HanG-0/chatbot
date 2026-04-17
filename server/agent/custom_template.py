from __future__ import annotations
from langchain.agents import Tool, AgentOutputParser
from langchain.prompts import StringPromptTemplate
from typing import List
from langchain.schema import AgentAction, AgentFinish

from configs import SUPPORT_AGENT_MODEL
from server.agent import model_container
from configs.basic_config import logger
class CustomPromptTemplate(StringPromptTemplate):
    template: str
    tools: List[Tool]

    def format(self, **kwargs) -> str:
        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought: "
        kwargs["agent_scratchpad"] = thoughts
        kwargs["tools"] = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])

        return self.template.format(**kwargs)
    
    def format_other(self, params: dict) -> str:
        """
        通用格式化方法：遍历字典，将所有 key-value 对格式化到模板上
        
        Args:
            params: 包含模板变量的字典，如 {"input": "问题", "background": "背景信息"}
        
        Returns:
            格式化后的字符串
        
        Example:
            template = "问题：{input}\n背景：{background}"
            params = {"input": "查询天气", "background": "今天是晴天"}
            result = format_other(params)
            # 结果: "问题：查询天气\n背景：今天是晴天"
        """
        # 将字典的 key-value 对添加到模板变量中
        format_vars = {}
        for key, value in params.items():
            format_vars[key] = value
        # 调用模板的 format 方法进行格式化
        return self.template.format(**format_vars)


class CustomOutputParser(AgentOutputParser):
    begin: bool = False
    def __init__(self):
        super().__init__()
        self.begin = True

    def parse(self, llm_output: str) -> AgentFinish | tuple[dict[str, str], str] | AgentAction:
        if not any(agent in model_container.MODEL for agent in SUPPORT_AGENT_MODEL) and self.begin:
            self.begin = False
            stop_words = ["Observation:"]
            min_index = len(llm_output)
            for stop_word in stop_words:
                index = llm_output.find(stop_word)
                if index != -1 and index < min_index:
                    min_index = index
                llm_output = llm_output[:min_index]

        logger.info(f"最终llm_output:\n{llm_output}")
        logger.info(f"Final Answer是否在最终llm_output: "+str("Final Answer:" in llm_output))
        # 检测字符串来判断是否停止
        if "Final Answer:" in llm_output:
            self.begin = True
            return AgentFinish(
                return_values={"output": llm_output.split("Final Answer:", 1)[-1].strip()},
                log=llm_output,
            )
        parts = llm_output.split("Action:")
        if len(parts) < 2:
            logger.info("调用agent工具失败，该回答为大模型自身能力的回答:")
            return AgentFinish(
                return_values={"output": f"{llm_output}"},
                log=llm_output,
            )

        action_parts = parts[1].split("Action Input:")
        if len(action_parts) < 2:
            logger.info("调用agent工具失败，缺少 Action Input 参数:\n")
            return AgentFinish(
                return_values={"output": f"{llm_output}"},
                log=llm_output,
            )

        action = action_parts[0].strip()
        action_input = action_parts[1].strip()
        try:
            ans = AgentAction(
                tool=action,
                tool_input=action_input.strip(" ").strip('"'),
                log=llm_output
            )
            return ans
        except:
            return AgentFinish(
                return_values={"output": f"调用agent失败: `{llm_output}`"},
                log=llm_output,
            )
