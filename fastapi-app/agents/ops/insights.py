"""评价文本关键词提取：字符 bigram + 停用词表，供 analysis.py 复用。

中文分词依赖（jieba 等）对"高频关键词"这一辅助信号来说过重，
bigram 方案可单测、零依赖、够用为准。"""
import re
from collections import Counter

# 中文高频停用词（常见虚词/标点/品类通用词，减少噪声）
_STOPWORDS = set(
    "的 了 是 在 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 "
    "自己 这 他 她 它 那 们 呢 吧 吗 啊 啦 哦 嘛 呀 嗯 哈 哎 哇 哈哈 "
    "可以 能 应该 可能 需要 想 要是 如果 因为 所以 但是 不过 然后 接着 还有 以及 "
    "什么 怎么 哪里 哪个 为什么 多少 几时 什么样 哪儿 怎样 如何 "
    "蛋糕 蛋 奶 油 款 个".split()
)


def _char_bigrams(text: str) -> list:
    """提取中文字符 bigram（2-gram），英文/数字忽略。"""
    text = re.sub(r'[^一-鿿]', '', text)
    return [text[i:i+2] for i in range(len(text) - 1) if len(text[i:i+2]) == 2]


def _count_keywords(texts: list, top_n: int = 20) -> list:
    """从文本列表中提取高频词（bigram 过滤停用词）。"""
    counter = Counter()
    for text in texts:
        for bigram in _char_bigrams(text):
            if bigram not in _STOPWORDS:
                counter[bigram] += 1
    return [{"keyword": k, "count": c} for k, c in counter.most_common(top_n)]
