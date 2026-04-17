import logging

from fastchat.conversation import Conversation
from server.model_workers.base import *
from fastchat import conversation as conv
import sys
import json
from server.model_workers.base import ApiEmbeddingsParams
from server.utils import get_httpx_client
from typing import List, Dict
from configs import logger, log_verbose


class MiniMaxWorker(ApiModelWorker):
    DEFAULT_EMBED_MODEL = "embo-01"

    def __init__(
        self,
        # *: 强制使用关键字参数，即调用时必须使用 参数名=值 的形式
        *,
        model_names: List[str] = ["minimax-api"],
        controller_addr: str = None,
        worker_addr: str = None,
        version: str = "MiniMax-M2.1",
        **kwargs,
    ):
        # 显式传入的参数合并到 kwargs 字典中:调用了dict的update方法
        kwargs.update(model_names=model_names, controller_addr=controller_addr, worker_addr=worker_addr)
        # 将键"context_len"的值设置为204800，如果没有则添加这个键
        kwargs.setdefault("context_len", 204800)
        super().__init__(**kwargs)
        self.version = version

    def validate_messages(self, messages: List[Dict]) -> List[Dict]:

        return messages

    def do_chat(self, params: ApiChatParams) -> Dict:
        # TODO: 支持指定回复要求，支持指定用户名称、AI名称
        logger.info(f'调用了Minimax的do_chat方法')
        params.load_config(self.model_names[0])

        url = 'https://api.minimax.chat/v1/text/chatcompletion_v2{pro}?GroupId={group_id}'
        pro = "_pro" if params.is_pro else ""
        headers = {
            "Authorization": f"Bearer {params.api_key}",
            "Content-Type": "application/json",
        }
        # 修复 invalid role 问题：MiniMax V2 只接受纯小写的system(系统提示词，模型角色)/user（用户输入）/assistant（输入历史）/user_system（用户角色）
        messages = self.validate_messages(params.messages)

        data = {
            "model": params.version,
            "stream": True,
            "messages": messages,
            "temperature": params.temperature,
            "top_p": params.top_p,
            # 最大输出token量
            "max_completion_tokens": 2048,
        }
        if log_verbose:
            logger.info(f'{self.__class__.__name__}:data: {data}')
            logger.info(f'{self.__class__.__name__}:url: {url.format(pro=pro, group_id=params.group_id)}')
            logger.info(f'{self.__class__.__name__}:headers: {headers}')

        with get_httpx_client() as client:
            response = client.stream("POST",
                                    url.format(pro=pro, group_id=params.group_id),
                                    headers=headers,
                                    json=data)
            with response as r:
                text = ""
                reasoning = ""
                for e in r.iter_lines():
                    if not e:
                        continue
                    if reasoning=="":
                        logger.info(f"流式输出内容：{e}")
                        # 流式输出，以data: [DONE]作为结尾
                    if e.startswith("data: [DONE]"):
                        break
                    if not e.startswith("data: "):
                        data = {
                                "error_code": 500,
                                "text": f"minimax返回错误的结果：{e}",
                                "error": {
                                    "message":  f"minimax返回错误的结果：{e}",
                                    "type": "invalid_request_error",
                                    "param": None,
                                    "code": None,
                                }
                        }
                        self.logger.error(f"请求 MiniMax API 时发生错误：{data}")
                        yield data
                        continue
                    
                    try:
                        data = json.loads(e[6:])
                    except Exception as ex:
                        self.logger.error(f"解析 MiniMax API 返回时发生错误：{e}, 错误：{ex}")
                        continue

                    if choices := data.get("choices"):
                        delta = choices[0].get("delta", {})
                        chunk = delta.get("content", "")
                        
                        # 检查是否有推理内容，并且同时拼接
                        reasoning_chunk = delta.get("reasoning_content", "")
                        if reasoning_chunk:
                            # 为了在前端区分，可以在推理内容前后做标识，或者直接拼接
                            reasoning = reasoning_chunk + reasoning
                        if chunk:
                            text += chunk
                            yield {"error_code": 0, "text": text}
                logger.info(f"================\nMiniMax 推理内容: {reasoning}\n================")
                logger.info(f"================\nMiniMax 最终输出内容: {text}\n================")

    def do_embeddings(self, params: ApiEmbeddingsParams) -> Dict:
        params.load_config(self.model_names[0])
        url = f"https://api.minimax.chat/v1/embeddings?GroupId={params.group_id}"

        headers = {
            "Authorization": f"Bearer {params.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": params.embed_model or self.DEFAULT_EMBED_MODEL,
            "texts": [],
            "type": "query" if params.to_query else "db",
        }
        if log_verbose:
            logger.info(f'{self.__class__.__name__}:data: {data}')
            logger.info(f'{self.__class__.__name__}:url: {url}')
            logger.info(f'{self.__class__.__name__}:headers: {headers}')

        with get_httpx_client() as client:
            result = []
            i = 0
            batch_size = 10
            while i < len(params.texts):
                texts = params.texts[i:i+batch_size]
                data["texts"] = texts
                r = client.post(url, headers=headers, json=data).json()
                if embeddings := r.get("vectors"):
                    result += embeddings
                elif error := r.get("base_resp"):
                    data = {
                                "code": error["status_code"],
                                "msg": error["status_msg"],
                                "error": {
                                    "message":  error["status_msg"],
                                    "type": "invalid_request_error",
                                    "param": None,
                                    "code": None,
                                }
                            }
                    self.logger.error(f"请求 MiniMax API 时发生错误：{data}")
                    return data
                i += batch_size
            return {"code": 200, "data": embeddings}

    def get_embeddings(self, params):
        # TODO: 支持embeddings
        print("embedding")
        print(params)

    def make_conv_template(self, conv_template: str = None, model_path: str = None) -> Conversation:
        # TODO: 确认模板是否需要修改
        return conv.Conversation(
            name=self.model_names[0],
            system_message="system: 你是一个金融纠纷调解机器人,你面对的是一个逾期未偿还债务的用户，你需要尽你所能结合所拥有的知识，尽力让对方达成还款意愿",
            messages=[],
            roles=["user", "assistant"],
            sep="####\n",
            stop_str="#",
        )


if __name__ == "__main__":
    import uvicorn
    from server.utils import MakeFastAPIOffline
    from fastchat.serve.model_worker import app

    worker = MiniMaxWorker(
        controller_addr="http://127.0.0.1:20001",
        worker_addr="http://127.0.0.1:21002",
    )
    sys.modules["fastchat.serve.model_worker"].worker = worker
    MakeFastAPIOffline(app)
    uvicorn.run(app, port=21002)
