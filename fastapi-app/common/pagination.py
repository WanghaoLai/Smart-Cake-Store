"""分页参数公共约束。

pageSize 无上限时 pageSize=1000000 等价于全表拉取 + 多表 prefetch，
内存与响应体积同时放大，是统计接口之外另一类资源滥用入口。
所有 selectPage 端点统一从这里取夹取后的参数。"""

MAX_PAGE_SIZE = 100


def clamp_page(page_num: int = 1, page_size: int = 10) -> tuple[int, int]:
    """页码下限 1（防负 offset），页大小夹取到 1..100。"""
    return max(int(page_num), 1), min(max(int(page_size), 1), MAX_PAGE_SIZE)
