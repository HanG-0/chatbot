#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动评估脚本：针对调解对话状态机的回复评估
支持指标：BLEU, ROUGE-L, 状态转移准确率, 流畅性/相关性/合理性/专业性
"""

import json
import re
import numpy as np
from collections import defaultdict
import time
import sys

# ================= 基础文本指标 =================
def simple_tokenize(text):
    """字符级分词（零依赖，适合中文基础评估）"""
    return list(text.strip())

class TextMetrics:
    @staticmethod
    def bleu_score(candidate, reference, n=4):
        cand = simple_tokenize(candidate)
        ref = simple_tokenize(reference)
        if not cand or not ref: return 0.0

        precisions = []
        for i in range(1, n+1):
            cand_ng = [tuple(cand[j:j+i]) for j in range(len(cand)-i+1)]
            ref_ng = [tuple(ref[k:k+i]) for k in range(len(ref)-i+1)]
            if not cand_ng:
                precisions.append(0.0)
                continue
            match = sum(1 for ng in cand_ng if ng in ref_ng)
            precisions.append(match / len(cand_ng))

        geo_mean = np.exp(np.mean(np.log([max(p, 1e-10) for p in precisions])))
        bp = min(1.0, np.exp(1 - len(ref)/len(cand))) if cand else 0
        return bp * geo_mean

    @staticmethod
    def rouge_l_score(candidate, reference):
        cand = simple_tokenize(candidate)
        ref = simple_tokenize(reference)
        if not cand or not ref: return 0.0

        m, n = len(cand), len(ref)
        dp = [[0]*(n+1) for _ in range(m+1)]
        for i in range(1, m+1):
            for j in range(1, n+1):
                if cand[i-1] == ref[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])

        lcs = dp[m][n]
        rec = lcs / len(ref)
        prec = lcs / len(cand)
        return 2 * rec * prec / (rec + prec) if (rec + prec) > 0 else 0.0

# ================= 调解场景评估器 =================
class MediationEvaluator:
    def __init__(self):
        self.valid_states = [
            "S0", "S1 信息确认", "S2 还款意愿确认",
            "S3 减免沟通", "S4 分期还款沟通", "S5 调解成功", "S6 调解失败"
        ]

    def evaluate(self, item):
        gt = item['ground_truth']
        pred = item['actual_output']
        exp_state = item['expected_state']
        act_state = item['actual_status']
        customer = item['customer']

        scores = {}
        # 1. 状态转移准确率（核心业务指标）
        scores['状态准确率'] = 1.0 if act_state == exp_state else 0.0

        # 2. 四维规则评分
        scores['流畅性'] = self._fluency(pred)
        scores['相关性'] = self._relevance(pred, gt, customer)
        scores['合理性'] = self._reasonableness(pred, exp_state)
        scores['专业性'] = self._professionalism(pred)

        # 综合质量分（不含状态准确率，避免维度混淆）
        scores['综合质量分'] = np.mean([
            scores['流畅性'], scores['相关性'], scores['合理性'], scores['专业性']
        ])
        return scores

    def _fluency(self, text):
        if len(text) < 3: return 2.0
        punct = sum(1 for c in text if c in '，。！？；：,.!?;:')
        if len(text) > 30 and punct == 0: return 3.5  # 长文本无标点
        if text.endswith(('。', '！', '？', ';', ':')): return 8.5
        # 检查重复/结巴
        if re.search(r'(.)\1{3,}', text): return 5.0
        return 7.0

    def _relevance(self, pred, gt, customer):
        # 关键数字覆盖（金额、天数、期数）
        nums_gt = re.findall(r'\d+(?:\.\d+)?', gt)
        nums_pred = re.findall(r'\d+(?:\.\d+)?', pred)
        num_match = sum(1 for n in nums_gt if any(n in np for np in nums_pred))
        num_score = (num_match / max(len(nums_gt), 1)) * 5.0

        # 业务关键词覆盖
        biz_kws = ['梁键荣', '借呗', '欠款', '逾期', '元', '天', '本金', '利息']
        kw_hit = sum(1 for kw in biz_kws if kw in pred or kw in customer)
        kw_score = min((kw_hit / max(len(biz_kws), 1)) * 5.0, 5.0)

        return min(num_score + kw_score, 10.0)

    def _reasonableness(self, pred, state):
        base = 6.0
        # 扣分项：命令式/威胁性语气
        aggressive = sum(1 for w in ['必须', '一定', '强制', '威胁', '立刻还钱', '马上', '否则'] if w in pred)
        base -= aggressive * 2.0
        # 加分项：共情/协商语气
        polite = sum(1 for w in ['您好', '请问', '建议', '协商', '理解', '困难', '核实'] if w in pred)
        base += polite * 1.2

        # 状态特异性校验
        if state == 'S1 信息确认' and not any(k in pred for k in ['确认', '核实', '是', '身份']):
            base -= 1.5
        if state in ['S3 减免沟通', 'S4 分期还款沟通'] and not any(k in pred for k in ['方案', '协商', '分期', '减免', '政策']):
            base -= 1.0

        return max(1.0, min(base, 10.0))

    def _professionalism(self, pred):
        terms = ['调解', '法院', '诉讼', '还款', '减免', '分期', '协商', '征信', '法律', '诉前', '调解员']
        count = sum(1 for t in terms if t in pred)
        score = 5.0 + min(count * 0.8, 4.0)
        if pred.startswith(('您好', '请问', '尊敬')): score += 0.5
        return min(score, 10.0)

# ================= 评估流程 =================
def load_and_evaluate(data_path):
    print(f"📥 正在加载数据: {data_path} ...")
    with open(data_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    dataset = []
    for idx, entry in enumerate(raw_data):
        content = entry.get('content', {})
        required = ['actual_output', 'ground_truth', 'expected_state', 'actual_status', 'former_state', 'customer']
        if all(k in content for k in required):
            content['_id'] = idx
            dataset.append(content)

    print(f"✅ 成功提取 {len(dataset)} 条有效样本")

    evaluator = MediationEvaluator()
    metrics = TextMetrics()
    results = []
    start = time.time()

    for i, item in enumerate(dataset):
        if (i + 1) % 500 == 0 or i == 0:
            print(f"⏳ 评估进度: {i+1}/{len(dataset)} | 耗时: {time.time()-start:.1f}s")

        bleu = metrics.bleu_score(item['actual_output'], item['ground_truth'])
        rouge = metrics.rouge_l_score(item['actual_output'], item['ground_truth'])
        qual = evaluator.evaluate(item)

        results.append({
            'id': item['_id'],
            'former_state': item['former_state'],
            'expected_state': item['expected_state'],
            'actual_status': item['actual_status'],
            'state_correct': qual['状态准确率'],
            'bleu': round(bleu, 4),
            'rouge': round(rouge, 4),
            'fluency': round(qual['流畅性'], 2),
            'relevance': round(qual['相关性'], 2),
            'reasonableness': round(qual['合理性'], 2),
            'professionalism': round(qual['专业性'], 2),
            'quality_avg': round(qual['综合质量分'], 2)
        })

    return results

def generate_report(results):
    if not results: return {"error": "无有效结果"}

    # 总体统计
    overall = {
        'total_samples': len(results),
        'avg_bleu': round(np.mean([r['bleu'] for r in results]), 4),
        'avg_rouge': round(np.mean([r['rouge'] for r in results]), 4),
        'avg_state_accuracy': round(np.mean([r['state_correct'] for r in results]), 4),
        'avg_quality_score': round(np.mean([r['quality_avg'] for r in results]), 2)
    }

    # 按预期状态分组
    state_groups = defaultdict(list)
    for r in results:
        state_groups[r['expected_state']].append(r)

    state_breakdown = {}
    for state, group in state_groups.items():
        state_breakdown[state] = {
            'count': len(group),
            'state_accuracy': round(np.mean([r['state_correct'] for r in group]), 4),
            'avg_quality': round(np.mean([r['quality_avg'] for r in group]), 2),
            'avg_bleu': round(np.mean([r['bleu'] for r in group]), 4),
            'avg_rouge': round(np.mean([r['rouge'] for r in group]), 4)
        }

    # 维度统计
    dims = ['fluency', 'relevance', 'reasonableness', 'professionalism']
    dim_map = {'fluency': '流畅性', 'relevance': '相关性', 'reasonableness': '合理性', 'professionalism': '专业性'}
    dimension_scores = {}
    for d in dims:
        vals = [r[d] for r in results]
        dimension_scores[dim_map[d]] = {
            'avg': round(np.mean(vals), 2),
            'std': round(np.std(vals), 2),
            'min': round(np.min(vals), 2),
            'max': round(np.max(vals), 2)
        }

    return {
        'overall_statistics': overall,
        'state_breakdown': state_breakdown,
        'dimension_scores': dimension_scores
    }

def main():
    print("="*60)
    print("🔍 调解对话自动评估系统 v2.0")
    print("="*60)

    data_file = '../agent_report/output_data.json'  # 请根据实际路径修改
    try:
        results = load_and_evaluate(data_file)
    except FileNotFoundError:
        print(f"❌ 找不到文件: {data_file}")
        print("💡 请确保数据文件路径正确，或修改 main() 中的 data_file 变量。")
        return
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        return

    print("\n📊 正在生成评估报告...")
    report = generate_report(results)

    # 终端输出
    print("\n" + "="*60)
    print("📈 总体统计")
    print(f"  样本总数       : {report['overall_statistics']['total_samples']}")
    print(f"  平均 BLEU      : {report['overall_statistics']['avg_bleu']:.4f}")
    print(f"  平均 ROUGE-L   : {report['overall_statistics']['avg_rouge']:.4f}")
    print(f"  状态转移准确率 : {report['overall_statistics']['avg_state_accuracy']:.2%}")
    print(f"  平均综合质量分 : {report['overall_statistics']['avg_quality_score']:.2f} / 10.00")

    print("\n📊 状态细分表现")
    for state, info in sorted(report['state_breakdown'].items()):
        print(f"  {state: <15} | 样本: {info['count']: <4} | 状态准确率: {info['state_accuracy']:.2%} | 质量分: {info['avg_quality']:.2f}")

    print("\n📐 维度得分详情")
    for dim, stats in report['dimension_scores'].items():
        print(f"  {dim: <6} | 平均: {stats['avg']:.2f} | 标准差: {stats['std']:.2f} | 范围: [{stats['min']:.1f} ~ {stats['max']:.1f}]")

    # 保存结果
    out_file = '../agent_report/evaluation_report.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({'results': results, 'report': report}, f, ensure_ascii=False, indent=2)
    print(f"\n💾 详细评估结果已保存至: {out_file}")
    print("="*60)

if __name__ == "__main__":
    main()