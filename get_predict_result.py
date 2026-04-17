from model_predict.predict_mediate_result import SimpleClassifier, get_result
from transformers import BertModel, BertTokenizer
import torch
import torch.nn as nn

from webui_pages.dialogue.dialogue import chat_box
from webui_pages.record.record_out import export2user


def get_predict_result():
    # 加载本地的BERT模型和tokenizer
    model_name = 'model_hub/bert-base-chinese'  # 本地模型的名称或路径
    tokenizer = BertTokenizer.from_pretrained(model_name)
    model = BertModel.from_pretrained(model_name)

    # Define and initialize the model
    input_size = 768
    hidden_size = 64
    output_size = 1
    # 初始化一个相同架构的模型
    loaded_model = SimpleClassifier(input_size, hidden_size, output_size)

    # 加载模型参数和优化器状态
    checkpoint = torch.load('model_hub/saved_model_threshold_0.5_300_epoch_lr_0.004.pth')
    loaded_model.load_state_dict(checkpoint['model_state_dict'])

    # 将模型设置为评估模式
    loaded_model.eval()

    user_word = export2user(chat_box)

    if len(user_word) == 0:
        return -1
    else:
        result = get_result(user_word, tokenizer, model, loaded_model)
        return result

