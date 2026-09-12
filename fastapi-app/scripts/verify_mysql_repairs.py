"""Isolated MySQL regression. Requires explicit CAKE_REPAIR_TEST=1 and cake_repair_ database.
Run after db/migrate.sh against the isolated instance; never target business data.
"""
import asyncio
import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tortoise import Tortoise, connections
from models import User, Goods, Orders, Address, Cart, WalletTransaction, PurchaseRequest, Admin
from settings import TORTOISE_ORM, DB_NAME
from api.orders import add, OrdersCreatePydantic
from api.cart import checkout, CartCheckoutPydantic
from domain.order_cancellation import cancel_purchase
from common.exception_handler import CustomException

async def main():
    if os.getenv('CAKE_REPAIR_TEST') != '1' or not DB_NAME.startswith('cake_repair_'):
        raise RuntimeError('Only an explicitly enabled isolated cake_repair_ database is allowed')
    browser_password = os.getenv('CAKE_REPAIR_BROWSER_PASSWORD')
    admin_password = os.getenv('CAKE_REPAIR_ADMIN_PASSWORD')
    if not browser_password or not admin_password:
        raise RuntimeError('Set CAKE_REPAIR_BROWSER_PASSWORD and CAKE_REPAIR_ADMIN_PASSWORD for isolated browser fixtures')
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        assert not await Admin.filter(username='222').exists(), 'Production seed contains demo administrator'
        assert not await User.filter(username='234').exists(), 'Production seed contains demo user'
        user=await User.create(username='mysql-'+uuid.uuid4().hex[:12],role='用户',balance=1000)
        identity={'user_id':user.id,'role':'用户'}
        goods=await Goods.create(name='MySQL 并发蛋糕',price=60,num=20,specs='6寸/8寸')
        address=await Address.create(user_id=user.id,name='买家',phone='13800000000',address='成交地址')
        def payload(key,**changes):
            data=dict(goodsId=goods.id,addressId=address.id,num=1,spec='8寸',request_id=key)
            data.update(changes)
            return OrdersCreatePydantic(**data)
        key=uuid.uuid4().hex
        results=await asyncio.gather(*(add(payload(key),identity) for _ in range(10)))
        assert len({r.data['order_no'] for r in results})==1
        assert (await User.get(id=user.id)).balance==Decimal(940)
        assert (await Goods.get(id=goods.id)).num==19
        print('PASS: 10 concurrent retries -> 1 order / 1 debit / 1 stock decrement')
        order=await Orders.filter(user_id=user.id).first()
        await asyncio.gather(*(cancel_purchase(identity,order_id=order.id) for _ in range(10)))
        assert (await User.get(id=user.id)).balance==Decimal(1000)
        assert (await Goods.get(id=goods.id)).num==20
        assert await WalletTransaction.filter(order_id=order.id,type='refund').count()==1
        print('PASS: 10 concurrent cancellations -> exactly one refund and stock restoration')
        cart=await Cart.create(user_id=user.id,goods_id=goods.id,num=2,spec='6寸')
        async def attempt(index):
            try:
                return await checkout(CartCheckoutPydantic(ids=[cart.id],addressId=address.id,request_id=uuid.uuid4().hex),identity)
            except CustomException:
                return None
        results=await asyncio.gather(*(attempt(i) for i in range(10)))
        assert sum(r is not None for r in results)==1
        assert (await User.get(id=user.id)).balance==Decimal(880)
        assert (await Goods.get(id=goods.id)).num==18
        print('PASS: 10 independent checkout intents on same cart -> only one purchase')
        await Goods.filter(id=goods.id).update(price=0)
        free=await add(payload(uuid.uuid4().hex),identity)
        free_order=await Orders.get(order_no=free.data['order_no'])
        assert free_order.total_price==0
        assert not await WalletTransaction.filter(order_id=free_order.id).exists()
        await cancel_purchase(identity,order_id=free_order.id)
        assert (await User.get(id=user.id)).balance==Decimal(880)
        print('PASS: zero-price purchase/cancel with real MySQL nonzero-ledger CHECK constraint')
        await Address.filter(id=address.id).update(address='被修改地址')
        assert (await Orders.get(id=order.id)).shipping_snapshot['address']=='成交地址'
        assert (await Orders.get(id=order.id)).spec=='8寸'
        print('PASS: persisted shipping/spec snapshot; production has no default accounts')
        # Keep known fixtures for browser end-to-end tests in this temporary database only.
        from common.auth import hash_password
        await User.create(username='repair-browser',name='测试买家',role='用户',password=hash_password(browser_password),balance=1000,must_change_password=False)
        browser_user=await User.get(username='repair-browser')
        await Address.create(user_id=browser_user.id,name='测试买家',phone='13800000000',address='上海市测试路1号',is_default=True)
        await Goods.create(name='系统测试草莓蛋糕',price=60,num=20,specs='6寸/8寸',unit='个',category_id=1,img='files/download/goods/1-1.jpeg')
        await Admin.create(username='repair-admin',name='测试管理员',role='管理员',password=hash_password(admin_password),must_change_password=False)
        print('PASS: browser fixtures prepared in isolated database')
    finally:
        await Tortoise.close_connections()

if __name__=='__main__':
    asyncio.run(main())
