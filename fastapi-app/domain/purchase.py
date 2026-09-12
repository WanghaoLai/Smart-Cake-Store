"""Purchase facts and money are committed together; user -> address/cart -> sorted goods locks."""
import hashlib
import json
import re
import uuid
from collections import Counter
from decimal import Decimal
from tortoise.transactions import in_transaction
from common.exception_handler import ConflictException, CustomException, ForbiddenException, NotFoundException
from common.time import utc_now, STORE_TIMEZONE
from models import Address, Cart, Goods, Orders, User, WalletTransaction, PurchaseRequest


def resolve_spec(goods, requested=""):
    choices = [s for s in re.split(r"[/／|、；,，\s]+", goods.specs or "") if s]
    if requested and requested not in choices:
        raise ConflictException("商品规格已变化，请重新选择")
    return requested or (choices[0] if choices else "")


def shipping(order):
    if order.shipping_snapshot is not None:
        return order.shipping_snapshot
    address = order.address
    return {k: getattr(address, k, None) for k in ("name", "phone", "address")}


async def purchase(user_id, request_id, *, address_id, goods_id=None, num=None, spec="", cart_ids=None):
    intent = {"address":address_id, "goods":goods_id,"num":num,"spec":spec,
              "cart": sorted(set(cart_ids)) if cart_ids is not None else None}
    fingerprint = hashlib.sha256(json.dumps(intent, sort_keys=True).encode()).hexdigest()
    async with in_transaction():
        user = await User.filter(id=user_id).select_for_update().first()
        if user is None:
            raise NotFoundException("用户不存在")
        previous = await PurchaseRequest.filter(user_id=user_id, request_id=request_id).first()
        if previous:
            if previous.fingerprint != fingerprint:
                raise ConflictException("同一请求编号不可用于不同订单，请重新确认购买")
            return previous.response
        address = await Address.filter(id=address_id, user_id=user_id).select_for_update().first()
        if address is None:
            raise ForbiddenException("收货地址不存在或不属于当前用户")
        snapshot = {k:getattr(address,k) for k in ("name","phone","address")}
        if cart_ids is not None:
            rows = await Cart.filter(id__in=cart_ids,user_id=user_id).order_by("id").select_for_update()
            if not rows or len(rows) != len(set(cart_ids)):
                raise NotFoundException("部分购物车条目不存在，请刷新购物车")
            lines = [(row.goods_id,row.num,row.spec) for row in rows]
        else:
            if not goods_id or not num or num <= 0:
                raise CustomException("请选择商品并填写大于 0 的购买数量")
            lines = [(goods_id,num,spec)]
        quantities = Counter()
        for gid,quantity,_ in lines:
            quantities[gid] += quantity
        products = {g.id:g for g in await Goods.filter(id__in=list(quantities)).order_by("id").select_for_update()}
        for gid,quantity in quantities.items():
            goods = products.get(gid)
            if goods is None:
                raise NotFoundException("商品不存在或已下架")
            if goods.num < quantity:
                raise ConflictException(f"「{goods.name}」库存不足，剩余 {goods.num} {goods.unit or '个'}")
        lines = [(gid,quantity,resolve_spec(products[gid],selected)) for gid,quantity,selected in lines]
        total = sum((products[gid].price * quantity for gid,quantity,_ in lines),Decimal(0))
        if user.balance < total:
            raise ConflictException(f"余额不足，本次需 ¥{total:.2f}，当前余额 ¥{user.balance:.2f}")
        order_nos = []
        for gid,quantity,selected in lines:
            goods = products[gid]
            amount = goods.price * quantity
            # A free order moves stock but never creates a zero-value money transfer.
            user.balance -= amount
            order = await Orders.create(user_id=user_id,goods_id=gid,address_id=address_id,
                num=quantity,spec=selected,shipping_snapshot=snapshot,total_price=amount,status="待发货",
                time=utc_now(),order_no=utc_now().astimezone(STORE_TIMEZONE).strftime("%Y%m%d%H%M%S")+uuid.uuid4().hex)
            goods.num -= quantity
            await goods.save(update_fields=["num"])
            if amount > 0:
                await WalletTransaction.create(user_id=user_id,type="payment",amount=-amount,
                    balance_after=user.balance,order_id=order.id,request_id=f"payment:{order.id}",remark=f"支付订单 {order.order_no}")
            order_nos.append(order.order_no)
        await user.save(update_fields=["balance"])
        if cart_ids is not None:
            deleted = await Cart.filter(id__in=cart_ids,user_id=user_id).delete()
            if deleted != len(lines):
                raise ConflictException("购物车已发生变化，请刷新后重试")
        response = {"balance":str(user.balance)}
        if cart_ids is not None:
            response.update(order_nos=order_nos,total=str(total))
        else:
            response["order_no"] = order_nos[0]
        await PurchaseRequest.create(user_id=user_id,request_id=request_id,fingerprint=fingerprint,response=response)
    return response
