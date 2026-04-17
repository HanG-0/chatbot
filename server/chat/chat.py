from fastapi import Body
from sse_starlette.sse import EventSourceResponse
from configs import LLM_MODELS, TEMPERATURE
from server.utils import wrap_done, get_ChatOpenAI
from langchain.chains import LLMChain
from langchain.callbacks import AsyncIteratorCallbackHandler
from typing import AsyncIterable
import asyncio
import json
from configs.basic_config import logger
from langchain.prompts.chat import ChatPromptTemplate
from typing import List, Optional, Union
from server.chat.utils import History
from langchain.prompts import PromptTemplate
from server.utils import get_prompt_template
from server.memory.conversation_db_buffer_memory import ConversationBufferDBMemory
from server.db.repository import add_message_to_db
from server.callback_handler.conversation_callback_handler import ConversationCallbackHandler


async def chat(query: str = Body(..., description="用户输入", examples=["恼羞成怒"]),
               conversation_id: str = Body("", description="对话框ID"),
               history_len: int = Body(-1, description="从数据库中取历史消息的数量"),
               history: Union[int, List[History]] = Body([],
                                                         description="历史对话，设为一个整数可以从数据库中读取历史消息",
                                                         examples=[[
                                                             {"role": "user",
                                                              "content": "我们来玩成语接龙，我先来，生龙活虎"},
                                                             {"role": "assistant", "content": "虎头虎脑"}]]
                                                         ),
               stream: bool = Body(False, description="流式输出"),
               model_name: str = Body(LLM_MODELS[0], description="LLM 模型名称。"),
               temperature: float = Body(TEMPERATURE, description="LLM 采样温度", ge=0.0, le=2.0),
               max_tokens: Optional[int] = Body(None, description="限制LLM生成Token数量，默认None代表模型最大值"),
               # top_p: float = Body(TOP_P, description="LLM 核采样。勿与temperature同时设置", gt=0.0, lt=1.0),
               prompt_name: str = Body("default", description="使用的prompt模板名称(在configs/prompt_config.py中配置)"),
               ):
    """
    仅针对llm_chat的情况下，进行与大模型的交流。（还有知识库/搜索引擎/智能体三种交流方式，对应不同的提示词语模版）
    """
    async def chat_iterator() -> AsyncIterable[str]:
        nonlocal history, max_tokens
        # langchain内置callback，会在LLM生成开始，每个token生成时，生成结束时分别触发
        callback = AsyncIteratorCallbackHandler()
        callbacks = [callback]
        memory = None

        # 先保存用户请求到数据库
        message_id = add_message_to_db(chat_type="llm_chat", query=query, conversation_id=conversation_id)
        # 回调：负责保存llm response到message db
        conversation_callback = ConversationCallbackHandler(conversation_id=conversation_id,
                                                            message_id=message_id,
                                                            chat_type="llm_chat",
                                                            query=query)
        callbacks.append(conversation_callback)

        if isinstance(max_tokens, int) and max_tokens <= 0:
            max_tokens = None

        model = get_ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            callbacks=callbacks,
        )

        # if history: # 优先使用前端传入的历史消息
        logger.info(f"传入的history: {history}")
        history = [History.from_data(h) for h in history]
        prompt_template = get_prompt_template("llm_chat", prompt_name)
        input_msg = History(role="user", content=prompt_template).to_msg_template(False)
        chat_prompt = ChatPromptTemplate.from_messages(
            [i.to_msg_template() for i in history] + [input_msg])
        # elif conversation_id and history_len > 0: # 前端要求从数据库取历史消息 （进入这个方法后，模型出现bug，不会输入内容）
        #     logger.info("走了带历史的模版")
        #     # 使用memory 时必须 prompt 必须含有memory.memory_key 对应的变量
        #     prompt_template = get_prompt_template("llm_chat", "with_history")
        #     chat_prompt = PromptTemplate.from_template(prompt_template,template_format="jinja2")
        #     # 根据conversation_id 获取message 列表进而拼凑 memory
        #     memory = ConversationBufferDBMemory(conversation_id=conversation_id,
        #                                         llm=model,
        #                                         message_limit=history_len)
        # else:
        #     logger.info("走了其他模版")
        #     prompt_template = get_prompt_template("llm_chat", prompt_name)
        #     input_msg = History(role="user", content=prompt_template).to_msg_template(False)
        #     chat_prompt = ChatPromptTemplate.from_messages([input_msg])
        logger.info(f"拼凑后的chat_prompt: {chat_prompt}")
        chain = LLMChain(prompt=chat_prompt, llm=model, memory=memory)

        # Begin a task that runs in the background.
        try:
            task = asyncio.create_task(wrap_done(
                chain.acall({"input": query}),
                callback.done),
            )
        except Exception as e:
            logger.error(f"Chain call failed: {e}", exc_info=True)
            yield json.dumps({"error": str(e), "message_id": message_id}, ensure_ascii=False)
            return

        if stream:
            async for token in callback.aiter():
                # Use server-sent-events to stream the response
                yield json.dumps(
                    {"text": token, "message_id": message_id},
                    ensure_ascii=False)
        else:
            answer = ""
            async for token in callback.aiter():
                answer += token
            yield json.dumps(
                {"text": answer, "message_id": message_id},
                ensure_ascii=False)

        await task

    return EventSourceResponse(chat_iterator())
