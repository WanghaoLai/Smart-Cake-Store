"""商品分析页（Ops.vue 四维分析）模拟数据填充脚本。

在现有库基础上补充订单与评价，目标是让分析页每个功能都有可验证数据：
  - 销量趋势：90 天窗口逐日分布（周末上浮），覆盖 7/30/90 三档时间窗
  - 环比：上一窗口同样有销量基线；"新品"角色仅在近 10 天有单（无基线场景）
  - 热销/滞销排行：商品分 热销/腰部/长尾 三档 + 专门滞销占压角色
  - 评价分析：内容带情感关键词；全局好评为主，"差评集中"角色差评占主导
  - 差评聚焦：每个问题商品绑定一个主投诉主题（太甜/量少/不新鲜/太小/太慢）
  - 库存分析：刻意把选中商品布成 健康/偏低/紧张/售罄 四档 + 滞销占压特例
  - 订单状态：按账龄自然分布（老单已评价、新单待发货、约 5% 已取消）

外键约束：订单/评价的用户、商品均取自现有表；一单仅一评（order_id 唯一约束）。
状态一致性：被评价订单 status='已评价'（与 reviews.py 状态机一致）；已取消订单不计销量。

用法：cd fastapi-app && python3 scripts/seed_analysis_data.py [--days 90] [--seed 42]
注意：脚本追加写入，重复执行会叠加数据（换 --seed 可得不同分布）。"""
import argparse
import asyncio
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# 脚本位于 fastapi-app/scripts/，应用代码与 .env 在上级目录
APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from dotenv import load_dotenv

load_dotenv(APP_DIR / ".env")

from tortoise import Tortoise

from settings import TORTOISE_ORM

# ---------------- 评价文案池（关键词刻意与分析词典对齐） ----------------
POS_RICH = [
    "很好吃，口感细腻，奶油不腻，下次还会回购",
    "蛋糕精致好看，收到惊喜，朋友都说赞",
    "新鲜又香甜，生日聚会全场好评，推荐！",
    "味道满意，送货快，包装完好",
    "慕斯入口即化，用料实在，值得这个价",
    "给爸妈订的，长辈都说好吃，很有面子",
]
POS_PLAIN = ["整体不错", "符合预期", "孩子很喜欢", "吃完再来"]
NEU = ["味道一般，造型还行", "中规中矩，不算惊艳", "凑合吧，路过买的"]
# 主投诉主题：差评聚焦（negative_focus）按商品定向分布
COMPLAINTS = {
    "太甜": ["太甜了，齁得慌，配茶才能吃", "甜度过高，老人没法吃"],
    "量少": ["量少，六寸比想象的小一圈", "分量缩水，性价比不高"],
    "不新鲜": ["不新鲜，奶油有点发酸", "送到已经不新鲜了，失望"],
    "太小": ["实物太小，跟图片差距大", "太小了，两个人不够吃"],
    "太慢": ["配送太慢，预约时间迟了两小时", "等太久，蛋糕都化了"],
}
NEG_GENERIC = ["失望，不建议购买", "踩雷了，不值这个价", "一般般，不会再买了"]


def _pick(pool):
    return random.choice(pool)


def review_content(rating: int, complaint: str | None) -> str:
    if rating >= 5:
        return _pick(POS_RICH)
    if rating == 4:
        return random.choice([_pick(POS_RICH), _pick(POS_PLAIN)])
    if rating == 3:
        return _pick(NEU)
    # 差评：70% 命中该商品的主投诉主题，保证差评聚焦定向可见
    if complaint and random.random() < 0.7:
        return _pick(COMPLAINTS[complaint])
    return _pick(NEG_GENERIC)


def roll_rating(profile: dict) -> int:
    """按商品人设抽星级：正常商品好评为主，差评集中商品反向。"""
    if profile["trouble"]:
        r = random.random()
        return 1 if r < 0.18 else 2 if r < 0.52 else 3 if r < 0.75 else 4
    r = random.random()
    return 5 if r < 0.55 else 4 if r < 0.82 else 3 if r < 0.90 else 2 if r < 0.97 else 1


async def main(days: int, seed: int) -> None:
    random.seed(seed)
    await Tortoise.init(config=TORTOISE_ORM)
    from models import Address, Goods, Orders, Review, User

    users = await User.filter(role="用户").values("id")
    user_ids = [u["id"] for u in users] or [1]
    user_weight = [5 if uid == user_ids[0] else 1 for uid in user_ids]  # 首用户为主力买家
    addr_by_user = {}
    for uid in user_ids:
        a = await Address.filter(user_id=uid).first()
        addr_by_user[uid] = a.id if a else None
    any_addr = next((v for v in addr_by_user.values() if v), None)

    all_goods = [g for g in await Goods.all() if g.price]
    if len(all_goods) < 25:
        raise SystemExit(f"商品不足 25 个（当前 {len(all_goods)}），请先运行 seed_goods.py")

    # ---- 商品人设：5 热销 / 8 腰部 / 12 长尾 ----
    picked = random.sample(all_goods, 25)
    hot, mid, low = picked[:5], picked[5:13], picked[13:]
    profiles = {}
    for g in hot:
        profiles[g.id] = {"rate": 0.45, "trend": random.choice([0.5, 0.25, 0.0, -0.3]),
                          "trouble": False, "complaint": None}
    # 角色一：热销但差评集中（评价分被拉低 → 综合等级 B/C 而非 A）
    trouble_goods = hot[0]
    profiles[trouble_goods.id] |= {"trouble": True, "complaint": "太甜", "trend": 0.1}
    for g in mid:
        profiles[g.id] = {"rate": 0.16, "trend": random.choice([0.3, 0.0, -0.2]),
                          "trouble": False, "complaint": random.choice(list(COMPLAINTS))}
    for g in low:
        profiles[g.id] = {"rate": 0.05, "trend": 0.0, "trouble": False,
                          "complaint": random.choice(list(COMPLAINTS))}
    # 角色二：新品——仅近 10 天有销量（环比无基线），且无评价（评价分中性基准）
    new_goods = low[0]
    profiles[new_goods.id] |= {"new": True}
    # 角色三：滞销占压——长尾但给高库存（库存可售天数 > 30 → 占压建议）
    dead_goods = low[1]

    # ---- 逐日生成订单 ----
    now = datetime.now()
    today = now.date()
    used_no = set(await Orders.all().values_list("order_no", flat=True))
    orders_plan = []  # (goods, user_id, addr_id, num, status, price, dt)
    review_plan = []  # (goods, user_id, rating, content, dt)

    for g in hot + mid + low:
        p = profiles[g.id]
        price = Decimal(str(g.price))
        for offset in range(days - 1, -1, -1):
            if p.get("new") and offset > 9:
                continue  # 新品 10 天前无销量
            d = today - timedelta(days=offset)
            growth = 1.0 + p["trend"] * (days - offset) / days
            weekend = 1.6 if d.weekday() >= 5 else 1.0
            lam = p["rate"] * max(0.1, growth) * weekend
            units = int(lam) + (1 if random.random() < lam - int(lam) else 0)
            while units > 0:
                num = 1 if random.random() < 0.86 else 2
                num = min(num, units)
                units -= num
                dt = datetime(d.year, d.month, d.day,
                              random.randint(9, 21), random.randint(0, 59))
                if dt > now:
                    dt = now - timedelta(minutes=random.randint(5, 120))
                uid = random.choices(user_ids, weights=user_weight)[0]
                # 状态按账龄自然分布
                age = (now - dt).days
                roll = random.random()
                if age < 7:
                    status = "待发货" if roll < 0.4 else "已发货" if roll < 0.9 else "待评价"
                elif age < 30:
                    status = "已评价" if roll < 0.3 else "待评价" if roll < 0.7 else "已发货" if roll < 0.95 else "已取消"
                else:
                    status = "已评价" if roll < 0.85 else "待评价" if roll < 0.95 else "已取消"
                orders_plan.append((g, uid, addr_by_user.get(uid) or any_addr, num, status, price, dt, p))
    random.shuffle(orders_plan)

    order_rows = []
    for i, (g, uid, addr_id, num, status, price, dt, p) in enumerate(orders_plan):
        order_no = f"{dt:%Y%m%d%H%M%S}{random.randint(1000, 9999)}{i % 10}"
        while order_no in used_no:
            order_no += "1"
        used_no.add(order_no)
        order_rows.append(Orders(
            order_no=order_no, num=num, user_id=uid, goods_id=g.id, address_id=addr_id,
            time=dt.strftime("%Y-%m-%d %H:%M:%S"), status=status,
            total_price=price * num,
        ))
    await Orders.bulk_create(order_rows, batch_size=100)

    # ---- 已评价订单补评价（1 单 1 评）----
    reviewed = [row for row in order_rows if row.status == "已评价"]
    for row in reviewed:
        p = profiles[row.goods_id]
        if p.get("new"):
            continue  # 新品无评价
        rating = roll_rating(p)
        rdt = min(
            datetime.strptime(row.time, "%Y-%m-%d %H:%M:%S") + timedelta(days=random.randint(1, 2), hours=random.randint(0, 12)),
            now,
        )
        review_plan.append(Review(
            goods_id=row.goods_id, user_id=row.user_id, order_id=None,
            rating=rating, content=review_content(rating, p["complaint"]),
            time=rdt.strftime("%Y-%m-%d %H:%M:%S"),
        ))
    # order_id 在 bulk_create 后才有自增主键，二次关联再写入
    created = await Orders.filter(order_no__in=[r.order_no for r in reviewed])
    id_by_no = {o.order_no: o.id for o in created}
    for r, row in zip(review_plan, reviewed):
        r.order_id = id_by_no[row.order_no]
    await Review.bulk_create(review_plan, batch_size=100)

    # ---- 库存布阵：刻意覆盖四档水位 + 两个特例 ----
    stock_plan = []
    for g in hot[1:3]:
        stock_plan.append((g, random.randint(40, 60)))          # 健康
    stock_plan.append((hot[3], random.randint(3, 5)))           # 紧张且有销量 → 预警
    stock_plan.append((hot[4], 0))                              # 售罄且有销量 → 紧急预警
    for g in mid[:4]:
        stock_plan.append((g, random.randint(8, 15)))           # 偏低
    stock_plan.append((dead_goods, 80))                         # 滞销占压：高库存低销量
    for g, num in stock_plan:
        g.num = num
        await g.save(update_fields=["num"])

    # ---- 汇总 + 自检（直接跑分析函数验证四维数据可用） ----
    from agents.ops.analysis import inventory_analysis, product_performance, review_analysis, sales_analysis

    status_count = {}
    for row in order_rows:
        status_count[row.status] = status_count.get(row.status, 0) + 1
    rating_count = {}
    for r in review_plan:
        rating_count[r.rating] = rating_count.get(r.rating, 0) + 1
    print(f"✅ 生成订单 {len(order_rows)} 条：{status_count}")
    print(f"✅ 生成评价 {len(review_plan)} 条：{rating_count}")
    print(f"✅ 库存布阵：{[(g.name, n) for g, n in stock_plan]}")

    inv = await inventory_analysis(days=30)
    print(f"\n—— 自检：库存水位 {inv['levels']}，预警 {inv['warning_count']} 个")
    for name, goods in [("热销-差评集中", trouble_goods), ("新品", new_goods), ("滞销占压", dead_goods)]:
        perf = await product_performance(goods.id, days=30)
        rev = await review_analysis(goods.id, days=30)
        print(f"—— {name}「{goods.name}」：综合 {perf['score']['total']}/{perf['score']['grade']}，"
              f"好评率 {rev['positive_rate']}%，差评聚焦 {[f['term'] for f in rev['negative_focus']][:3]}")
    trend = await sales_analysis(hot[1].id, days=30)
    print(f"—— 趋势自检「{hot[1].name}」：30 天 {trend['total_qty']} 件，环比 {trend['qty_change_pct']}%")

    await Tortoise.close_connections()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="商品分析页模拟数据填充")
    parser.add_argument("--days", type=int, default=90, help="时间窗（默认 90 天）")
    parser.add_argument("--seed", type=int, default=42, help="随机种子（默认 42）")
    args = parser.parse_args()
    asyncio.run(main(args.days, args.seed))
