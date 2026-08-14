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
    phone = fields.CharField(max_length=255, null=True)
    # 结构化地址：省/市/区县 ID + 冗余名称（地区表只读，冗余存储避免每次 3 表 join）
    province = fields.ForeignKeyField('models.Province', null=True)
    province_name = fields.CharField(max_length=32, null=True)
    city = fields.ForeignKeyField('models.City', null=True)
    city_name = fields.CharField(max_length=64, null=True)
    town = fields.ForeignKeyField('models.Town', null=True)
    town_name = fields.CharField(max_length=64, null=True)
    detail = fields.CharField(max_length=255, null=True)
    # 历史字段保留向后兼容；新增/更新时由 省+市+区+detail 自动拼接
    address = fields.CharField(max_length=255, null=True)
    # 默认地址：每个用户最多 1 条 is_default=True；事务内互斥更新
    is_default = fields.BooleanField(default=False)

    class Meta:
        table = 'address'


class Province(Model):
    id = fields.IntField(pk=True, null=False)
    name = fields.CharField(max_length=32, null=True)
    area = fields.CharField(max_length=64, null=True)

    class Meta:
        table = 'tb_province'


class City(Model):
    id = fields.IntField(pk=True, null=False)
    name = fields.CharField(max_length=64, null=True)
    province = fields.ForeignKeyField('models.Province', null=True)

    class Meta:
        table = 'tb_city'


class Town(Model):
    id = fields.IntField(pk=True, null=False)
    name = fields.CharField(max_length=64, null=True)
    city = fields.ForeignKeyField('models.City', null=True)

    class Meta:
        table = 'tb_town'

class Orders(Model):
    id = fields.IntField(pk=True, null=False)
    order_no = fields.CharField(max_length=255, null=True)
    num = fields.IntField(null=True)
    user = fields.ForeignKeyField('models.User', null=True)
    goods = fields.ForeignKeyField('models.Goods', null=True)
    address = fields.ForeignKeyField('models.Address', null=True)
    time = fields.CharField(max_length=255, null=True)
    # 订单状态：待发货（默认）/ 已发货 / 待评价 / 已评价 / 已取消
    # 用定长短字符串而非独立状态表：状态集合小且稳定，避免多一次 join，前端直接展示
    status = fields.CharField(max_length=32, default='待发货', null=True)

    class Meta:
        table = 'orders'


class Review(Model):
    """商品评价：1 订单 1 评价（unique order_id），公开可见，管理员可回复。
    images 存 JSON 数组字符串，避免引入图片子表。"""
    id = fields.IntField(pk=True, null=False)
    goods = fields.ForeignKeyField('models.Goods', related_name='reviews', null=True)
    user = fields.ForeignKeyField('models.User', null=True)
    # 一单一评：order_id 唯一约束防止重复评价
    order = fields.ForeignKeyField('models.Orders', related_name='reviews', null=True, unique=True)
    rating = fields.IntField(null=True)  # 1-5 星
    content = fields.TextField(null=True)
    images = fields.TextField(null=True)  # JSON 数组字符串，如 ["url1","url2"]
    reply = fields.TextField(null=True)  # 管理员回复
    reply_time = fields.CharField(max_length=32, null=True)
    time = fields.CharField(max_length=32, null=True)

    class Meta:
        table = 'review'

class Notice(Model):
    id = fields.IntField(pk=True, null=False)
    name = fields.CharField(max_length=255, null=True)
    content = fields.CharField(max_length=255, null=True)
    time = fields.CharField(max_length=255, null=True)

    class Meta:
        table = 'notice'


class Conversation(Model):
    id = fields.IntField(pk=True, null=False)
    # User 与 Admin 使用独立表，数字主键可能重叠；会话归属必须由角色 + ID 联合标识。
    user_id = fields.IntField()
    owner_role = fields.CharField(max_length=32, default='用户')
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



