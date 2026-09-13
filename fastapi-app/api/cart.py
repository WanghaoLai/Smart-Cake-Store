"""购物车 API：增删改查、勾选状态、角标数量、批量结算。

结算在同一事务内完成「库存校验/扣减 → 订单创建 → 余额支付 → 购物车清理」，
任一步失败整体回滚，保证购物车与订单/库存/余额的最终一致。
行锁顺序与购买/取消一致（用户 → 购物车 → 商品按 id 升序），避免交叉死锁。"""
from functools import wraps
import inspect

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from tortoise.transactions import in_transaction

from common.auth import get_current_customer, get_current_user
from common.exception_handler import ConflictException, NotFoundException
from common.result import Result
from common.time import format_store_time
from models import Cart, Goods, User

router = APIRouter(prefix="/cart", dependencies=[Depends(get_current_user)])


class CartAddPydantic(BaseModel):
    goodsId: int
    spec: str = Field(default="", max_length=255)
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
    request_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


def serialized_cart(fn):
    # All cart mutations serialize with checkout on the same owner row, across processes.
    @wraps(fn)
    async def wrapped(*args, **kwargs):
        bound = inspect.signature(fn).bind(*args, **kwargs)
        owner = bound.arguments["current_user"]
        async with in_transaction():
            user = await User.filter(id=owner["user_id"]).select_for_update().first()
            if user is None:
                raise NotFoundException("用户不存在")
            return await fn(*args, **kwargs)
    return wrapped


async def _cart_row(cart_id: int, user_id: int) -> Cart:
    cart = await Cart.get_or_none(id=cart_id, user_id=user_id).prefetch_related('goods')
    if cart is None:
        raise NotFoundException("购物车条目不存在")
    return cart


async def _ensure_stock(goods: Goods, num: int) -> None:
    if goods.num < num:
        raise ConflictException(f"「{goods.name}」库存不足，剩余 {goods.num} {goods.unit or '个'}")


@router.post("/add")
@serialized_cart
async def add(payload: CartAddPydantic, current_user: dict = Depends(get_current_customer)):
    from domain.purchase import resolve_spec
    goods = await Goods.filter(id=payload.goodsId).select_for_update().first()
    if goods is None:
        raise NotFoundException("商品不存在")
    selected = resolve_spec(goods, payload.spec)
    rows = await Cart.filter(user_id=current_user["user_id"], goods_id=goods.id)
    await _ensure_stock(goods, sum(r.num for r in rows) + payload.num)
    existing = next((r for r in rows if r.spec == selected), None)
    if existing:
        existing.num += payload.num
        await existing.save(update_fields=["num"])
    else:
        await Cart.create(user_id=current_user["user_id"], goods_id=goods.id, num=payload.num, spec=selected)
    return Result.success()


@router.get("/list")
async def list_items(current_user: dict = Depends(get_current_customer)):
    """当前用户购物车全量列表（含商品实时信息），按加入时间倒序。"""
    rows = await Cart.filter(user_id=current_user["user_id"]).prefetch_related('goods').order_by('-id')
    items = [
        {
            "id": row.id,
            "num": row.num,
            "spec": row.spec,
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
@serialized_cart
async def update_num(cart_id: int, payload: CartUpdatePydantic, current_user: dict = Depends(get_current_customer)):
    cart = await _cart_row(cart_id, user_id=current_user["user_id"])
    others = await Cart.filter(user_id=current_user["user_id"], goods_id=cart.goods_id).exclude(id=cart.id)
    await _ensure_stock(cart.goods, payload.num + sum(r.num for r in others))
    cart.num = payload.num
    await cart.save(update_fields=['num'])
    return Result.success()


@router.delete("/remove/{cart_id}")
@serialized_cart
async def remove_one(cart_id: int, current_user: dict = Depends(get_current_customer)):
    cart = await _cart_row(cart_id, current_user["user_id"])
    await cart.delete()
    return Result.success()


@router.post("/remove-batch")
@serialized_cart
async def remove_batch(payload: CartIdsPydantic, current_user: dict = Depends(get_current_customer)):
    """批量删除。带 user_id 过滤：混入他人条目 id 不生效也无法探测。"""
    deleted = await Cart.filter(id__in=payload.ids, user_id=current_user["user_id"]).delete()
    return Result.success({"deleted": deleted})


@router.put("/select/{cart_id}")
@serialized_cart
async def select_one(cart_id: int, payload: CartSelectPydantic, current_user: dict = Depends(get_current_customer)):
    cart = await _cart_row(cart_id, current_user["user_id"])
    cart.selected = payload.selected
    await cart.save(update_fields=['selected'])
    return Result.success()


@router.put("/select-all")
@serialized_cart
async def select_all(payload: CartSelectPydantic, current_user: dict = Depends(get_current_customer)):
    await Cart.filter(user_id=current_user["user_id"]).update(selected=payload.selected)
    return Result.success()


@router.post("/checkout")
async def checkout(payload: CartCheckoutPydantic, current_user: dict = Depends(get_current_customer)):
    from domain.purchase import purchase
    return Result.success(await purchase(current_user["user_id"], payload.request_id,
        address_id=payload.addressId, cart_ids=payload.ids))
