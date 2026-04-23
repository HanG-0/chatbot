from langchain.memory import ConversationBufferWindowMemory

from server.agent.custom_agent.ChatGLM3Agent import initialize_glm3_agent
from server.agent.tools_select import tools, tool_names
from server.agent.callbacks import CustomAsyncIteratorCallbackHandler, Status
from langchain.agents import LLMSingleActionAgent, AgentExecutor
from server.agent.custom_template import CustomOutputParser, CustomPromptTemplate
from fastapi import Body
from sse_starlette.sse import EventSourceResponse
from configs import LLM_MODELS, TEMPERATURE, HISTORY_LEN, Agent_MODEL
from server.utils import wrap_done, get_ChatOpenAI, get_prompt_template
from langchain.chains import LLMChain
from typing import AsyncIterable, Optional
import asyncio
from typing import List
from server.chat.utils import History
import json
from server.agent import model_container
from server.knowledge_base.kb_service.base import get_kb_details
from configs.basic_config import logger
from server.db.redis_manager import get_redis


async def agent_chat(query: str = Body(..., description="用户输入", examples=["恼羞成怒"]),
                     history: List[History] = Body([],
                                                   description="历史对话",
                                                   examples=[[
                                                       {"role": "user", "content": "请使用知识库工具查询今天北京天气"},
                                                       {"role": "assistant",
                                                        "content": "使用天气查询工具查询到今天北京多云，10-14摄氏度，东北风2级，易感冒"}]]
                                                   ),
                     stream: bool = Body(False, description="流式输出"),
                     model_name: str = Body(LLM_MODELS[0], description="LLM 模型名称。"),
                     temperature: float = Body(TEMPERATURE, description="LLM 采样温度", ge=0.0, le=1.0),
                     max_tokens: Optional[int] = Body(None, description="限制LLM生成Token数量，默认None代表模型最大值"),
                     prompt_name: str = Body("default",
                                             description="使用的prompt模板名称(在configs/prompt_config.py中配置)"),
                     # top_p: float = Body(TOP_P, description="LLM 核采样。勿与temperature同时设置", gt=0.0, lt=1.0),
                     ):
    history = [History.from_data(h) for h in history]

    async def agent_chat_iterator(
            query: str,
            history: Optional[List[History]],
            model_name: str = LLM_MODELS[0],
            prompt_name: str = prompt_name,
    ) -> AsyncIterable[str]:
        nonlocal max_tokens
        callback = CustomAsyncIteratorCallbackHandler()
        if isinstance(max_tokens, int) and max_tokens <= 0:
            max_tokens = None

        model = get_ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            callbacks=[callback],
        )

        ## 传入全局变量来实现agent调用
        kb_list = {x["kb_name"]: x for x in get_kb_details()}
        model_container.DATABASE = {name: details['kb_info'] for name, details in kb_list.items()}

        if Agent_MODEL:
            ## 如果有指定使用Agent模型来完成任务
            model_agent = get_ChatOpenAI(
                model_name=Agent_MODEL,
                temperature=temperature,
                max_tokens=max_tokens,
                callbacks=[callback],
            )
            model_container.MODEL = model_agent
        else:
            model_container.MODEL = model

            # 模版和解析器配置
            prompt_template = get_prompt_template("agent_chat", prompt_name)
            prompt_template_agent = CustomPromptTemplate(
                template=prompt_template,
                tools=tools,
                input_variables=["input", "intermediate_steps", "history"]
            )

        # 把history转成agent的memory
        memory = ConversationBufferWindowMemory(k=HISTORY_LEN * 2)
        for message in history:
            # 检查消息的角色
            if message.role == 'user':
                # 添加用户消息
                memory.chat_memory.add_user_message(message.content)
            elif message.role == 'assistant':
                # 添加AI消息
                memory.chat_memory.add_ai_message(message.content)

        # 永远不进入的分支
        if "chatglm3" in model_container.MODEL.model_name:
            agent_executor = initialize_glm3_agent(
                llm=model,
                tools=tools,
                callback_manager=None,
                # Langchain Prompt is not constructed directly here, it is constructed inside the GLM3 agent.
                prompt=prompt_template_agent,
                input_variables=["input", "intermediate_steps", "history"],
                memory=memory,
                verbose=True,
            )
        else:
            # 使用状态驱动+包含工作流的agent
            from server.agent.workflow_executor import (
                create_auto_workflow_executor
            )
            from configs.status_prompt import STATUS_TRANSFER_PROMPT,status_transfer_dict

            r = get_redis()
            status_store = r.get("status_store")
            if status_store is None:
                logger.info("agent_chat: redis中status_store为空，设置为默认值")
                status_store = "S0"
            status_transfer_prompt = STATUS_TRANSFER_PROMPT.format(
                current_status = status_store,
                transfer_condition = status_transfer_dict.get(status_store)
            )

            # 使用自动化执行器（工作流）
            logger.info("[Workflow] Using StateDrivenAgent")
            # 这里是工作流执行器
            auto_executor = create_auto_workflow_executor(
                # 工作流中，不再使用原来的llm
                prompt_template=status_transfer_prompt,
                memory=memory
            )

            while True:
                try:
                    # 执行简单对话
                    task = asyncio.create_task(
                        auto_executor.execute(query, callbacks=[callback])
                    )
                    # 获取对话结果
                    result = await task
                    # 尝试解析结果（如果返回的是JSON格式）
                    try:
                        result_dict = json.loads(result)
                        # 处理工作流状态更新
                        if "workflow_state" in result_dict:
                            new_state = result_dict["workflow_state"]
                            await r.setex("status_store",3000, new_state)
                            logger.info(f"更新状态到{new_state}")
                    except (json.JSONDecodeError, TypeError):
                        # 如果不是JSON格式，直接使用结果作为文本输出
                        pass
                    
                    break
                except Exception as e:
                    logger.info(f"Workflow execution error: {e}")
                    break
            # 等3s再请求
            await asyncio.sleep(3)
            # 创建输出解析器（解析 LLM 的 Action 和 Final Answer

            from configs.status_prompt import STATUS_PROMPT_TEMPLATES
            background_info = json.loads(r.get("background_info"))
            # 根据状态查询当前提示词
            logger.info(f"当前状态为{status_store}")
            logger.info(f"当前信息为{background_info}")
            status_prompt = STATUS_PROMPT_TEMPLATES.get(status_store).format(**background_info)
            # 拼接背景提示词
            prompt_template_agent.template = "background : "+ status_prompt + "\n" +prompt_template_agent.template
            output_parser = CustomOutputParser()
            llm_chain = LLMChain(llm=model, prompt=prompt_template_agent)

            # 补充状态识别agent的处理
            agent = LLMSingleActionAgent(
                llm_chain=llm_chain,
                output_parser=output_parser,
                stop=["\nObservation:", "Observation"],
                allowed_tools=tool_names,
            )
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                memory=memory,
                verbose=True,
            )
        while True:
            try:
                task = asyncio.create_task(wrap_done(
                    agent_executor.acall(query, callbacks=[callback], include_run_info=True),
                    callback.done))
                break
            except:
                pass

        if stream:
            try:
                async for chunk in callback.aiter():
                    try:
                        tools_use = []
                        # Use server-sent-events to stream the response
                        if chunk is None:
                            logger.warning("收到 None chunk，跳过")
                            continue
                            
                        data = json.loads(chunk)
                        if data["status"] == Status.start or data["status"] == Status.complete:
                            continue
                        elif data["status"] == Status.error:
                            tools_use.append("\n```\n")
                            tool_name = data.get("tool_name", "未知工具")
                            tools_use.append("工具名称: " + tool_name)
                            tools_use.append("工具状态: " + "调用失败")
                            error_msg = data.get("error", "未知错误")
                            tools_use.append("错误信息: " + error_msg)
                            tools_use.append("重新开始尝试")
                            tools_use.append("\n```\n")
                            yield json.dumps({"tools": tools_use}, ensure_ascii=False)
                        elif data["status"] == Status.tool_finish:
                            tools_use.append("\n```\n")
                            tool_name = data.get("tool_name", "未知工具")
                            tools_use.append("工具名称: " + tool_name)
                            tools_use.append("工具状态: " + "调用成功")
                            input_str = data.get("input_str", "无输入信息")
                            tools_use.append("工具输入: " + input_str)
                            output_str = data.get("output_str", "无输出信息")
                            tools_use.append("工具输出: " + output_str)
                            tools_use.append("\n```\n")
                            yield json.dumps({"tools": tools_use}, ensure_ascii=False)
                        elif data["status"] == Status.agent_finish:
                            final_answer = data.get("final_answer", "")
                            yield json.dumps({"final_answer": final_answer}, ensure_ascii=False)
                        else:
                            llm_token = data.get("llm_token", "")
                            yield json.dumps({"answer": llm_token}, ensure_ascii=False)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析错误: {e}, chunk内容: {chunk}")
                        continue
                    except KeyError as e:
                        logger.error(f"字段缺失错误: {e}, data内容: {data}")
                        continue
                    except Exception as e:
                        logger.error(f"流式处理未知错误: {e}")
                        continue
            except Exception as e:
                logger.error(f"流式响应处理失败: {e}")
                yield json.dumps({"answer": f"系统错误: {str(e)}"}, ensure_ascii=False)

        else:
            answer = ""
            final_answer = ""
            try:
                async for chunk in callback.aiter():
                    try:
                        # Use server-sent-events to stream the response
                        if chunk is None:
                            logger.warning("收到 None chunk，跳过")
                            continue
                            
                        data = json.loads(chunk)
                        if data["status"] == Status.start or data["status"] == Status.complete:
                            continue
                        if data["status"] == Status.error:
                            answer += "\n```\n"
                            tool_name = data.get("tool_name", "未知工具")
                            answer += "工具名称: " + tool_name + "\n"
                            answer += "工具状态: " + "调用失败" + "\n"
                            error_msg = data.get("error", "未知错误")
                            answer += "错误信息: " + error_msg + "\n"
                            answer += "\n```\n"
                        if data["status"] == Status.tool_finish:
                            answer += "\n```\n"
                            tool_name = data.get("tool_name", "未知工具")
                            answer += "工具名称: " + tool_name + "\n"
                            answer += "工具状态: " + "调用成功" + "\n"
                            input_str = data.get("input_str", "无输入信息")
                            answer += "工具输入: " + input_str + "\n"
                            output_str = data.get("output_str", "无输出信息")
                            answer += "工具输出: " + output_str + "\n"
                            answer += "\n```\n"
                        if data["status"] == Status.agent_finish:
                            final_answer = data.get("final_answer", "")
                        else:
                            llm_token = data.get("llm_token", "")
                            answer += llm_token
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析错误: {e}, chunk内容: {chunk}")
                        continue
                    except KeyError as e:
                        logger.error(f"字段缺失错误: {e}, data内容: {data}")
                        continue
                    except Exception as e:
                        logger.error(f"流式处理未知错误: {e}")
                        continue
            except Exception as e:
                logger.error(f"非流式响应处理失败: {e}")
                answer += f"\n系统错误: {str(e)}"
                
            yield json.dumps({"answer": answer, "final_answer": final_answer}, ensure_ascii=False)
        await task

    return EventSourceResponse(agent_chat_iterator(query=query,
                                                 history=history,
                                                 model_name=model_name,
                                                 prompt_name=prompt_name),
                             )
