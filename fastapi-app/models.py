from tortoise.models import Model
from tortoise import fields

# 创建Admin的Model
class Admin(Model):
    id = fields.IntField(pk=True, null=False)
    username = fields.CharField(max_length=255, null=True)
    password = fields.CharField(max_length=255, null=True)
    name = fields.CharField(max_length=255, null=True)
    avatar = fields.CharField(max_length=255, null=True)
    role = fields.CharField(max_length=255, null=True)
    must_change_password = fields.BooleanField(default=True)

    class Meta:
        table = 'admin'


# 创建User的Model
class User(Model):
    id = fields.IntField(pk=True, null=False)
    username = fields.CharField(max_length=255, null=True)
    password = fields.CharField(max_length=255, null=True)
    name = fields.CharField(max_length=255, null=True)
    avatar = fields.CharField(max_length=255, null=True)
    role = fields.CharField(max_length=255, null=True)
    must_change_password = fields.BooleanField(default=True)

    class Meta:
        table = 'user'


# 创建Category的Model
class Category(Model):
    id = fields.IntField(pk=True, null=False)
    name = fields.CharField(max_length=255, null=True)

    class Meta:
        table = 'category'


# 创建Goods的Model
class Goods(Model):
    id = fields.IntField(pk=True, null=False)
    name = fields.CharField(max_length=255, null=True)
    price = fields.FloatField(null=True)
    description = fields.CharField(max_length=255, null=True)
    # 详情页扩展字段：从第一性原理出发，用户购买前需要确认
    # 配料（过敏原）/ 详细介绍 / 规格 / 保质期 / 净含量 / 产地 / 适用人数
    detail = fields.TextField(null=True)
    ingredients = fields.CharField(max_length=500, null=True)
    specs = fields.CharField(max_length=255, null=True)
    shelf_life = fields.CharField(max_length=100, null=True)
    weight = fields.CharField(max_length=100, null=True)
    origin = fields.CharField(max_length=100, null=True)
    serves = fields.CharField(max_length=100, null=True)
    img = fields.CharField(max_length=255, null=True)
    num = fields.IntField(null=True)
    unit = fields.CharField(max_length=255, null=True)
    category = fields.ForeignKeyField('models.Category', null=True)

    class Meta:
        table = 'goods'

class Address(Model):
    id = fields.IntField(pk=True, null=False)
    user = fields.ForeignKeyField('models.User', null=True)
    name = fields.CharField(max_length=255, null=True)
    address = fields.CharField(max_length=255, null=True)
    phone = fields.CharField(max_length=255, null=True)

    class Meta:
        table = 'address'

class Orders(Model):
    id = fields.IntField(pk=True, null=False)
    order_no = fields.CharField(max_length=255, null=True)
    num = fields.IntField(null=True)
    user = fields.ForeignKeyField('models.User', null=True)
    goods = fields.ForeignKeyField('models.Goods', null=True)
    address = fields.ForeignKeyField('models.Address', null=True)
    time = fields.CharField(max_length=255, null=True)

    class Meta:
        table = 'orders'

class Notice(Model):
    id = fields.IntField(pk=True, null=False)
    name = fields.CharField(max_length=255, null=True)
    content = fields.CharField(max_length=255, null=True)
    time = fields.CharField(max_length=255, null=True)

    class Meta:
        table = 'notice'


class Conversation(Model):
    id = fields.IntField(pk=True, null=False)
    user = fields.ForeignKeyField('models.User', related_name='conversations')
    title = fields.CharField(max_length=255, default='新对话')
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'conversation'


class Message(Model):
    id = fields.IntField(pk=True, null=False)
    conversation = fields.ForeignKeyField('models.Conversation', related_name='messages')
    role = fields.CharField(max_length=20)  # 'user' 或 'assistant'
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'message'


class Favorite(Model):
    id = fields.IntField(pk=True, null=False)
    user = fields.ForeignKeyField('models.User', null=True)
    goods = fields.ForeignKeyField('models.Goods', null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'favorite'


class Knowledge(Model):
    id = fields.IntField(pk=True, null=False)
    filename = fields.CharField(max_length=255, null=True)
    original_name = fields.CharField(max_length=255, null=True)
    file_size = fields.IntField(null=True)
    chunk_count = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'knowledge'


class IndexTask(Model):
    """向量索引 outbox：MySQL 业务提交后写入，后台任务异步同步到 ChromaDB。
    ChromaDB 视为可重建的派生索引，索引失败不影响业务事务。"""
    id = fields.IntField(pk=True, null=False)
    entity_type = fields.CharField(max_length=32, default='goods')
    entity_id = fields.IntField()
    action = fields.CharField(max_length=16)  # upsert | delete
    status = fields.CharField(max_length=16, default='pending')  # pending | done | failed
    attempts = fields.IntField(default=0)
    last_error = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'index_task'



