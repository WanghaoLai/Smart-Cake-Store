"""购物车 API：增删改查、勾选状态、角标数量、批量结算。

结算在同一事务内完成「库存校验/扣减 → 订单创建 → 余额支付 → 购物车清理」，
任一步失败整体回滚，保证购物车与订单/库存/余额的最终一致。
行锁顺序与 orders.py 一致（商品按 id 升序 → 用户），避免交叉死锁。"""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from common.auth import get_current_customer, get_current_user
from common.exception_handler import ConflictException, CustomException, ForbiddenException, NotFoundException
from common.result import Result
from common.time import STORE_TIMEZONE, format_store_time, utc_now
from domain.order_status import ORDER_PENDING
from models import Address, Cart, Goods, Orders, User, WalletTransaction

router = APIRouter(prefix="/cart", dependencies=[Depends(get_current_user)])


class CartAddPydantic(BaseModel):
    goodsId: int
    num: int = Field(default=1, ge=1)


class CartUpdatePydantic(BaseModel):
    num: int = Field(ge=1)


class CartSelectPydantic(BaseModel):
    selected: bool


class CartIdsPydantic(BaseModel):
    ids: list[int] = Field(min_length=1)


class CartCheckoutPydantic(BaseModel):
    ids: list[int] = Field(min_length=1)
    addressId: int


def _generate_order_no() -> str:
    return utc_now().astimezone(STORE_TIMEZONE).strftime('%Y%m%d%H%M%S') + uuid.uuid4().hex[:6].upper()


async def _cart_row(cart_id: int, user_id: int) -> Cart:
    cart = await Cart.get_or_none(id=cart_id, user_id=user_id).prefetch_related('goods')
    if cart is None:
        raise NotFoundException("购物车条目不存在")
    return cart


async def _ensure_stock(goods: Goods, num: int) -> None:
    if goods.num < num:
        raise ConflictException(f"「{goods.name}」库存不足，剩余 {goods.num} {goods.unit or '个'}")


@router.post("/add")
async def add(payload: CartAddPydantic, current_user: dict = Depends(get_current_customer)):
    """加入购物车。同商品已存在则数量累加（合计不超过当前库存），否则新建。"""
    goods = await Goods.get_or_none(id=payload.goodsId)
    if goods is None:
        raise NotFoundException("商品不存在")
    existing = await Cart.get_or_none(user_id=current_user["user_id"], goods_id=payload.goodsId)
    target_num = payload.num + (existing.num if existing else 0)
    await _ensure_stock(goods, target_num)
    if existing:
        existing.num = target_num
        await existing.save(update_fields=['num'])
    else:
        try:
            await Cart.create(
                user_id=current_user["user_id"],
                goods_id=payload.goodsId,
                num=payload.num,
            )
        except IntegrityError:
            # 并发首次加购撞唯一键：退化为累加路径重试一次
            existing = await Cart.get_or_none(user_id=current_user["user_id"], goods_id=payload.goodsId)
            if existing is None:
                raise ConflictException("加入购物车失败，请重试")
            existing.num += payload.num
            await existing.save(update_fields=['num'])
    return Result.success()


@router.get("/list")
async def list_items(current_user: dict = Depends(get_current_customer)):
    """当前用户购物车全量列表（含商品实时信息），按加入时间倒序。"""
    rows = await Cart.filter(user_id=current_user["user_id"]).prefetch_related('goods').order_by('-id')
    items = [
        {
            "id": row.id,
            "num": row.num,
            "selected": row.selected,
            "createdAt": format_store_time(row.created_at),
            "goodsId": row.goods.id,
            "goodsName": row.goods.name,
            "goodsImg": row.goods.img,
            "goodsPrice": str(row.goods.price),
            "goodsUnit": row.goods.unit,
            "stock": row.goods.num,
        }
        for row in rows
    ]
    return Result.success({"list": items, "total": len(items)})


@router.get("/count")
async def count_items(current_user: dict = Depends(get_current_customer)):
    """角标数量：购物车内商品总件数（各条目数量之和）。"""
    rows = await Cart.filter(user_id=current_user["user_id"]).values_list('num', flat=True)
    return Result.success({"count": sum(rows)})


@router.put("/update/{cart_id}")
async def update_num(cart_id: int, payload: CartUpdatePydantic, current_user: dict = Depends(get_current_customer)):
    cart = await _cart_row(cart_id, user_id=current_user["user_id"])
    await _ensure_stock(cart.goods, payload.num)
    cart.num = payload.num
    await cart.save(update_fields=['num'])
    return Result.success()


@router.delete("/remove/{cart_id}")
async def remove_one(cart_id: int, current_user: dict = Depends(get_current_customer)):
    cart = await _cart_row(cart_id, current_user["user_id"])
    await cart.delete()
    return Result.success()


@router.post("/remove-batch")
async def remove_batch(payload: CartIdsPydantic, current_user: dict = Depends(get_current_customer)):
    """批量删除。带 user_id 过滤：混入他人条目 id 不生效也无法探测。"""
    deleted = await Cart.filter(id__in=payload.ids, user_id=current_user["user_id"]).delete()
    return Result.success({"deleted": deleted})


@router.put("/select/{cart_id}")
async def select_one(cart_id: int, payload: CartSelectPydantic, current_user: dict = Depends(get_current_customer)):
    cart = await _cart_row(cart_id, current_user["user_id"])
    cart.selected = payload.selected
    await cart.save(update_fields=['selected'])
    return Result.success()


@router.put("/select-all")
async def select_all(payload: CartSelectPydantic, current_user: dict = Depends(get_current_customer)):
    await Cart.filter(user_id=current_user["user_id"]).update(selected=payload.selected)
    return Result.success()


@router.post("/checkout")
async def checkout(payload: CartCheckoutPydantic, current_user: dict = Depends(get_current_customer)):
    """批量结算：勾选条目各生成一笔订单（Orders 为单商品模型）。

    单事务内完成：地址归属校验 → 购物车条目归属校验 → 商品按 id 升序加锁
    并校验库存 → 用户加锁校验余额 → 逐条创建订单/扣库存/记流水（余额快照
    逐笔滚动）→ 落余额 → 清理购物车。订单号唯一冲突整体重试（上一轮事务
    已回滚，不会二次扣减）。"""
    created_at = utc_now()
    user_id = current_user["user_id"]

    for _ in range(2):
        try:
            async with in_transaction():
                address = await Address.get_or_none(id=payload.addressId, user_id=user_id)
                if address is None:
                    raise ForbiddenException("收货地址不存在或不属于当前用户")

                cart_rows = await Cart.filter(id__in=payload.ids, user_id=user_id)
                if len(cart_rows) != len(set(payload.ids)):
                    raise NotFoundException("部分购物车条目不存在")
                # 商品按 id 升序加锁，与单商品下单/取消共用顺序，避免死锁
                goods_map = {
                    g.id: g for g in await Goods.filter(
                        id__in=[r.goods_id for r in cart_rows]
                    ).order_by('id').select_for_update()
                }
                for row in cart_rows:
                    goods = goods_map.get(row.goods_id)
                    if goods is None:
                        raise NotFoundException("部分商品已下架，请刷新购物车")
                    await _ensure_stock(goods, row.num)

                total = sum(goods_map[r.goods_id].price * r.num for r in cart_rows)
                user = await User.filter(id=user_id).select_for_update().first()
                if user is None:
                    raise NotFoundException("用户不存在")
                if user.balance < total:
                    shortage = total - user.balance
                    raise ConflictException(
                        f"余额不足，本次需 ¥{total:.2f}，当前余额 ¥{user.balance:.2f}，还差 ¥{shortage:.2f}"
                    )

                order_nos = []
                running_balance = user.balance
                for row in cart_rows:
                    goods = goods_map[row.goods_id]
                    amount = goods.price * row.num
                    running_balance -= amount
                    order = await Orders.create(
                        user_id=user_id,
                        goods_id=goods.id,
                        address_id=payload.addressId,
                        num=row.num,
                        time=created_at,
                        order_no=_generate_order_no(),
                        status=ORDER_PENDING,
                        total_price=amount,
                    )
                    goods.num -= row.num
                    await goods.save(update_fields=['num'])
                    await WalletTransaction.create(
                        user_id=user_id,
                        type="payment",
                        amount=-amount,
                        balance_after=running_balance,
                        order_id=order.id,
                        request_id=f"payment:{order.id}",
                        remark=f"支付订单 {order.order_no}",
                    )
                    order_nos.append(order.order_no)

                user.balance = running_balance
                await user.save(update_fields=['balance'])
                await Cart.filter(id__in=payload.ids, user_id=user_id).delete()
            break
        except IntegrityError:
            continue
    else:
        raise CustomException("订单号生成冲突，请重试")

    return Result.success({"order_nos": order_nos, "balance": user.balance, "total": total})
