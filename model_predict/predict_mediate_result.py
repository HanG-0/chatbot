import numpy as np
import torch
import torch.nn as nn


class SimpleClassifier(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(SimpleClassifier, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x


def get_emb(sentences, tokenizer, model):
    sentences = sentences[:60]
    # 将字符串转换为BERT输入格式
    inputs = tokenizer(sentences, return_tensors="pt", padding=True, truncation=True)

    # 获取BERT模型的输出
    with torch.no_grad():
        outputs = model(**inputs)

    # 解压缩模型输出元组
    last_hidden_states = outputs[0]

    # 提取每个句子的最后一层的嵌入
    embeddings = last_hidden_states[:, 0, :]
    # 计算所有嵌入的平均值
    average_embedding = torch.mean(embeddings, dim=0)

    # 转换为NumPy数组
    average_embedding_np = average_embedding.numpy()
    # 归一化
    normalized_embedding = average_embedding_np / np.linalg.norm(average_embedding_np) if np.linalg.norm(
        average_embedding_np) != 0 else np.zeros_like(average_embedding_np)
    return normalized_embedding
    # 输出最终的768维嵌入向量


def get_result(user_word, tokenizer, model, loaded_model):
    embedded_sentence = get_emb(user_word, tokenizer, model)
    # 将嵌入向量转换为PyTorch张量
    X_test_tensor = torch.Tensor(np.array([embedded_sentence]))
    # Forward pass for the test set using the loaded model
    with torch.no_grad():
        test_outputs = loaded_model(X_test_tensor)
        # 计算二分类评估指标
        predicted_labels = (torch.sigmoid(test_outputs) > 0.5).float()  # 大于0.5的认为是正类别
    predicted_labels = int(predicted_labels.item())

    return predicted_labels
