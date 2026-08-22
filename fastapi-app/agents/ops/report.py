"""商品分析报告渲染与事实摘要。

关键设计：统计全部在 SQL 层完成（analysis.py），LLM 输入是结构化摘要
而非原始行——token 成本 O(1) 于数据规模，且天然无幻觉事实。"""


def _md_table(headers: list, rows: list) -> str:
    if not rows:
        return "_（无数据）_\n"
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines) + "\n"


def build_product_markdown(facts: dict, summary: str | None) -> str:
    """把 POST /ops/analysis/ai 落库的 facts 渲染为 Markdown 报告。

    summary 为空（LLM 降级）时呈现确定性事实表，保证报告永远可下载。"""
    perf = facts.get("performance", {})
    score = perf.get("score", {})
    rev = facts.get("reviews", {})
    sales = facts.get("sales", {})
    inv = facts.get("inventory", {})
    dims = score.get("dimensions", {})

    out = [
        f"# 商品分析报告 · {facts.get('goods_name', '—')}",
        "",
        f"- 统计窗口：近 {facts.get('days', 30)} 天",
        f"- 生成时间：{facts.get('generated_at', '')}",
        "",
        "## AI 分析结论",
        "",
        summary if summary else "_(AI 模型暂不可用，以下为确定性数据报告)_",
        "",
        "## 综合表现",
        "",
        f"- **综合得分：{score.get('total', '—')} / 100（等级 {score.get('grade', '—')}）**",
        f"- 销量分 {dims.get('sales', {}).get('score', '—')}（权重 40%） · "
        f"评价分 {dims.get('review', {}).get('score', '—')}（权重 40%） · "
        f"库存分 {dims.get('inventory', {}).get('score', '—')}（权重 20%）",
        f"- 当前库存：{perf.get('stock', '—')}",
        "",
    ]
    for s in score.get("suggestions", []):
        out.append(f"- {s}")
    out += ["", "## 评价分析", ""]
    sentiment = rev.get("sentiment", {})
    focus = "、".join(f"{i['term']}×{i['count']}" for i in rev.get("negative_focus", []))
    keywords = "、".join(k["keyword"] for k in rev.get("keywords", [])[:8])
    out += [
        f"- 平均星级 {rev.get('avg_rating', '—')}，好评率 {rev.get('positive_rate', 0)}%"
        f"（好评 {sentiment.get('好评', 0)} / 中评 {sentiment.get('中评', 0)} / 差评 {sentiment.get('差评', 0)}）",
        f"- 高频关键词：{keywords or '—'}",
        f"- 差评聚焦：{focus or '无'}",
        "",
        "### 差评原文（最多 10 条）",
        "",
        _md_table(
            ["星级", "内容", "用户", "时间"],
            [[r["rating"], r["content"][:60], r["user_name"], r["time"]]
             for r in rev.get("negative_reviews", [])],
        ),
        "## 销量分析",
        "",
        f"- 窗口内销量 {sales.get('total_qty', 0)} 件 / {sales.get('order_count', 0)} 单，"
        f"营收 ¥{sales.get('total_revenue', 0)}",
    ]
    change = sales.get("qty_change_pct")
    out.append(f"- 环比上一窗口：{'+' if (change or 0) >= 0 else ''}{change}%\n" if change is not None else "- 环比：上一窗口无销量，无基线\n")
    trend_rows = [(d["date"], d["qty"]) for d in sales.get("daily_trend", []) if d["qty"] > 0]
    out += ["", "### 按天销量", "", _md_table(["日期", "销量"], trend_rows)]

    out += ["## 库存分析（全店）", ""]
    levels = inv.get("levels", {})
    out += [
        f"- 水位分布：健康 {levels.get('健康', 0)} / 偏低 {levels.get('偏低', 0)} / "
        f"紧张 {levels.get('紧张', 0)} / 售罄 {levels.get('售罄', 0)}",
        f"- 库存资金占用 ¥{inv.get('total_inventory_value', 0)}，预警商品 {inv.get('warning_count', 0)} 个",
        "",
        "### 预警商品清单",
        "",
        _md_table(
            ["商品", "库存", "窗口销量", "可售天数"],
            [[w["name"], f"{w['stock']}{w['unit']}", w["sold_qty"], w["days_of_stock"] or "—"]
             for w in inv.get("warning_list", [])],
        ),
        "---",
        "",
        "*本报告由智能商城导购与运营平台生成，数据来自 MySQL 实时查询。*",
    ]
    return "\n".join(out)


def build_fact_digest(facts: dict) -> str:
    """把服务端已核实的四维事实压成 agent 可直接引用的真实数据摘要。

    设计动机：工具调用是模型自主行为，可能只调一个工具就作答（出现过
    "暂无销量数据"的失实结论）。注入摘要保证结论必然基于真实订单销量
    与真实用户评价——与客服 agent 的 Grounding 哲学一致。"""
    sales = facts.get("sales", {})
    reviews = facts.get("reviews", {})
    perf = facts.get("performance", {})
    score = perf.get("score", {})
    dims = score.get("dimensions", {})
    sentiment = reviews.get("sentiment", {})

    # 销量明细指标从 daily_trend 推导（摘要比 facts 多给"最高单日/零销量天数/近7天"）
    trend = sales.get("daily_trend", [])
    best_day = max(trend, key=lambda d: d["qty"], default=None)
    days_with_sales = sum(1 for d in trend if d["qty"] > 0)
    last7 = sum(d["qty"] for d in trend[-7:])

    lines = [
        f"【服务端已核实的真实数据】商品「{facts.get('goods_name', '—')}」(ID {facts.get('goods_id')})，"
        f"统计窗口：近 {facts.get('days')} 天。",
        "",
        "一、真实订单销量（orders 表，已排除已取消订单）",
        f"- 窗口销量 {sales.get('total_qty', 0)} 件 / {sales.get('order_count', 0)} 单，"
        f"营收 ¥{sales.get('total_revenue', 0)}",
    ]
    change = sales.get("qty_change_pct")
    lines.append(f"- 环比上一窗口：{('+' if (change or 0) >= 0 else '')}{change}%\n"
                 if change is not None else "- 环比：上一窗口无销量基线\n")
    if best_day and best_day["qty"] > 0:
        lines.append(f"- 单日峰值：{best_day['date']}（{best_day['qty']} 件）；"
                     f"{days_with_sales}/{len(trend)} 天有销量；近 7 天 {last7} 件")

    lines += ["", "二、真实用户评价（review 表）"]
    if reviews.get("total"):
        lines.append(
            f"- 共 {reviews['total']} 条，平均 {reviews.get('avg_rating')} 星，好评率 "
            f"{reviews.get('positive_rate')}%（好评 {sentiment.get('好评', 0)} / "
            f"中评 {sentiment.get('中评', 0)} / 差评 {sentiment.get('差评', 0)}）"
        )
        keywords = "、".join(f"{k['keyword']}×{k['count']}" for k in reviews.get("keywords", [])[:6])
        if keywords:
            lines.append(f"- 高频关键词：{keywords}")
        focus = "、".join(f"{f['term']}×{f['count']}" for f in reviews.get("negative_focus", [])[:5])
        if focus:
            lines.append(f"- 差评聚焦：{focus}")
        for r in reviews.get("negative_reviews", [])[:3]:
            lines.append(f"  · 真实差评摘录「{r['content'][:40]}」（{r['rating']}★ {r['time'][:10]}）")
        for r in reviews.get("positive_reviews", [])[:2]:
            lines.append(f"  · 真实好评摘录「{r['content'][:40]}」（{r['rating']}★ {r['time'][:10]}）")
    else:
        lines.append("- 窗口内暂无评价（评价分按中性基准 60 计，需在结论中说明）")

    lines += [
        "",
        "三、综合表现（销量 40% + 评价 40% + 库存 20%）",
        f"- 总分 {score.get('total')}/{100}（等级 {score.get('grade')}）；"
        f"销量分 {dims.get('sales', {}).get('score')}、评价分 {dims.get('review', {}).get('score')}、"
        f"库存分 {dims.get('inventory', {}).get('score')}；当前库存 {perf.get('stock')} 份",
        "",
        "请完全基于以上真实数据生成分析结论；如需全店热销/滞销对比或库存预警明细，"
        "可调用 analyze_product_sales（不带 goods_id）或 analyze_inventory_status 补充。"
        "结论中禁止出现上述数据与工具结果之外的任何数字。",
    ]
    return "\n".join(lines)


__all__ = ["build_fact_digest", "build_product_markdown"]
