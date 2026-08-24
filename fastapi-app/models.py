from tortoise.models import Model
from tortoise import fields

# 创建Admin的Model
class Admin(Model):
    id = fields.IntField(pk=True, null=False)
    username = fields.CharField(max_length=255, null=True, unique=True)
    password = fields.CharField(max_length=255, null=True)
    name = fields.CharField(max_length=255, null=True)
    avatar = fields.CharField(max_length=255, null=True)
    role = fields.CharField(max_length=255, null=True)
    must_change_password = fields.BooleanField(default=True)
    token_version = fields.IntField(default=0)

    class Meta:
        table = 'admin'


# 创建User的Model
class User(Model):
    id = fields.IntField(pk=True, null=False)
    username = fields.CharField(max_length=255, null=True, unique=True)
    password = fields.CharField(max_length=255, null=True)
    name = fields.CharField(max_length=255, null=True)
    avatar = fields.CharField(max_length=255, null=True)
    role = fields.CharField(max_length=255, null=True)
    must_change_password = fields.BooleanField(default=True)
    token_version = fields.IntField(default=0)
    # 钱包余额只允许服务端在事务内变更；DECIMAL 避免浮点金额误差。
    balance = fields.DecimalField(max_digits=12, decimal_places=2, default=0)

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
    name = fields.CharField(max_length=255, null=False)
    # 金额字段：DECIMAL(10,2)，浮点会在 sum 聚合中累积精度误差（0.1+0.2≠0.3）
    price = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
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
    num = fields.IntField(null=False)
    unit = fields.CharField(max_length=255, null=True)
    category = fields.ForeignKeyField('models.Category', null=True, on_delete=fields.SET_NULL)

    class Meta:
        table = 'goods'

class Address(Model):
    id = fields.IntField(pk=True, null=False)
    user = fields.ForeignKeyField('models.User', null=True, on_delete=fields.RESTRICT)
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
    # 唯一约束：订单号是用户查询订单的主键式凭据，同号会导致按号查询命中他人订单
    order_no = fields.CharField(max_length=255, null=True, unique=True)
    num = fields.IntField(null=True)
    user = fields.ForeignKeyField('models.User', null=True, on_delete=fields.RESTRICT)
    goods = fields.ForeignKeyField('models.Goods', null=True, on_delete=fields.RESTRICT)
    address = fields.ForeignKeyField('models.Address', null=True, on_delete=fields.RESTRICT)
    time = fields.DatetimeField(null=False)
    # 订单状态：待发货（默认）/ 已发货 / 待评价 / 已评价 / 已取消
    # 用定长短字符串而非独立状态表：状态集合小且稳定，避免多一次 join，前端直接展示
    status = fields.CharField(max_length=32, default='待发货', null=True)
    # 成交价快照：下单时锁定商品单价 × 数量。管理员事后改价时，
    # 历史订单金额与报表不随之漂移（审计要求）
    total_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True)

    class Meta:
        table = 'orders'
        indexes = (("user", "id"), ("goods", "time"), ("status", "time"))


class WalletTransaction(Model):
    """不可变钱包流水。

    balance_after 是每笔交易完成后的快照，便于用户核对和后台审计；
    request_id 唯一，防止充值按钮重试或网络重放造成重复入账。
    """
    id = fields.IntField(pk=True, null=False)
    user = fields.ForeignKeyField('models.User', related_name='wallet_transactions', on_delete=fields.RESTRICT)
    type = fields.CharField(max_length=16)  # recharge / payment / refund
    amount = fields.DecimalField(max_digits=12, decimal_places=2)
    balance_after = fields.DecimalField(max_digits=12, decimal_places=2)
    payment_method = fields.CharField(max_length=32, null=True)
    status = fields.CharField(max_length=16, default='success')
    order = fields.ForeignKeyField('models.Orders', null=True, on_delete=fields.RESTRICT)
    request_id = fields.CharField(max_length=64, unique=True)
    remark = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'wallet_transaction'
        indexes = (("user", "created_at"), ("order", "type"))


class Review(Model):
    """商品评价：1 订单 1 评价（unique order_id），公开可见，管理员可回复。
    images 存 JSON 数组字符串，避免引入图片子表。"""
    id = fields.IntField(pk=True, null=False)
    goods = fields.ForeignKeyField('models.Goods', related_name='reviews', null=True, on_delete=fields.RESTRICT)
    user = fields.ForeignKeyField('models.User', null=True, on_delete=fields.RESTRICT)
    # 一单一评：order_id 唯一约束防止重复评价
    order = fields.ForeignKeyField(
        'models.Orders', related_name='reviews', null=True, unique=True, on_delete=fields.RESTRICT,
    )
    rating = fields.IntField(null=True)  # 1-5 星
    content = fields.TextField(null=True)
    images = fields.TextField(null=True)  # JSON 数组字符串，如 ["url1","url2"]
    reply = fields.TextField(null=True)  # 管理员回复
    reply_time = fields.DatetimeField(null=True)
    time = fields.DatetimeField(null=False)

    class Meta:
        table = 'review'

class Notice(Model):
    id = fields.IntField(pk=True, null=False)
    name = fields.CharField(max_length=255, null=True)
    content = fields.CharField(max_length=255, null=True)
    time = fields.DatetimeField(null=False)

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
    # AI 可观测性：LLM 调用计量与归因（仅 assistant 消息有值；缺失记 NULL）
    prompt_tokens = fields.IntField(null=True)
    completion_tokens = fields.IntField(null=True)
    latency_ms = fields.IntField(null=True)
    model = fields.CharField(max_length=64, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'message'


class Favorite(Model):
    id = fields.IntField(pk=True, null=False)
    user = fields.ForeignKeyField('models.User', null=True, on_delete=fields.CASCADE)
    goods = fields.ForeignKeyField('models.Goods', null=True, on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'favorite'
        unique_together = (("user", "goods"),)


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
    status = fields.CharField(max_length=16, default='pending')  # pending | processing | done | failed
    attempts = fields.IntField(default=0)
    last_error = fields.TextField(null=True)
    claim_token = fields.CharField(max_length=36, null=True)
    processing_started_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'index_task'


class OpsReport(Model):
    """运营日报：每次生成落库，事实+LLM摘要并列，历史可回看。"""
    id = fields.IntField(pk=True, null=False)
    days = fields.IntField(default=7)
    summary = fields.TextField(null=True)  # LLM 摘要（失败时 NULL）
    facts = fields.JSONField(null=True)    # 原始 SQL 事实快照
    model = fields.CharField(max_length=64, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'ops_report'


class AuditLog(Model):
    """敏感操作审计：密码重置、账号增删、订单状态强制变更、知识库删除。

    best-effort 写入（业务成功后落记录，失败仅记日志），因此不设外键——
    审计行允许引用已被删除的目标；operator_name 冗余存储防账号删除后不可读。"""
    id = fields.IntField(pk=True, null=False)
    operator_role = fields.CharField(max_length=16)  # 用户 / 管理员 / 系统
    operator_id = fields.IntField()
    operator_name = fields.CharField(max_length=255, null=True)
    action = fields.CharField(max_length=64)          # 如 user.reset_password
    target_type = fields.CharField(max_length=32, null=True)
    target_id = fields.IntField(null=True)
    detail = fields.JSONField(null=True)
    ip = fields.CharField(max_length=64, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'audit_log'


class Notification(Model):
    """订单站内通知：状态变更事务内同步写入（同事务保证不丢）。

    接收者由 角色 + user_id 联合标识（User/Admin 独立建表，主键可能重叠，
    与 Conversation 同一归属模型）；读取侧轮询，分钟级实时性足够。"""
    id = fields.IntField(pk=True, null=False)
    user_id = fields.IntField()
    owner_role = fields.CharField(max_length=16, default='用户')
    type = fields.CharField(max_length=32)          # order.shipped / order.cancelled
    title = fields.CharField(max_length=128)
    content = fields.CharField(max_length=500, null=True)
    is_read = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'notification'


class Cart(Model):
    """购物车：用户-商品-数量，同商品合并为一行（UNIQUE(user, goods)）。

    非资金审计根（区别于订单）：用户注销/商品删除时级联清理。
    selected 持久化勾选状态，跨设备同步结算选择。"""
    id = fields.IntField(pk=True, null=False)
    user = fields.ForeignKeyField('models.User', on_delete=fields.CASCADE)
    goods = fields.ForeignKeyField('models.Goods', on_delete=fields.CASCADE)
    num = fields.IntField(default=1)
    selected = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = 'cart'
        unique_together = ('user', 'goods')



