# 代码优化报告

## 优化前后指标对比

| 指标 | 原始代码 | 优化后 | 变化 | 评级(优化前→优化后) |
|------|---------|--------|------|------------------|
| 有效代码行数 LOC | 290 | 259 | -31 | 中等→中等 |
| 平均函数行数 | 21.2 | 8.5 | -12.7 | 中等→✅优秀 |
| 平均圈复杂度 | 5.8 | 2.9 | -2.9 | 中等→✅优秀 |
| 重复代码率 | 20.7% | 8.1% | -12.6% | ❌差→⚠️中等 |
| Halstead难度 | 5.2 | 5.0 | -0.2 | ✅简单→✅简单 |
| 可维护性指数 MI | 32.7 | 35.5 | +2.8 | 🔥差→🔥差 |

## 优化过程

### 第1轮：识别核心问题
通过 `python indicator.py` 分析原始代码，发现三大问题：
1. **重复代码率高达20.7%**：`create_order` 中对 `product_db` 遍历了 **3次**（库存检查、总价计算、扣减库存），`cancel_order` 中又有一次完全重复的库存返还循环
2. **函数过长**：平均21.2行，多个函数超过30行
3. **全局变量污染**：所有数据直接暴露为全局列表，无封装

### 第2轮：消除重复循环（核心优化）
将商品相关操作封装进 `Database` 类：
- `prepare_order_products()`：**单次调用**完成查找+库存检查+价格计算，替代 `create_order` 中原来的三次循环
- `restore_stock()`：取消订单时复用此方法，**彻底消除**了 `cancel_order` 中与 `create_order` 重复的库存遍历
- **效果**：重复代码率从 20.7% 骤降至 8.3%

### 第3轮：缩小函数粒度
- `calc_discount()`：从 `create_order` 中抽出独立纯函数，替代硬编码 if-else 链
- `_advance_order()`：将 `ship_order` 和 `complete_order` 的共同模式（查订单→校验状态→更新状态→记日志）抽取为统一 helper，圈复杂度进一步下降
- `Result` 对象：替代 `print` 语句，实现结构化返回值，便于后续扩展

### 第4轮：消除 Enum 陷阱，使用整数状态常量
之前使用 `Enum("OrderStatus", ...)` 时 Python 自动分配整数 1-5，导致 `CANCELLED=5` 与 STATUS_MAP 不匹配。改用简洁的 `class S:` 类定义整数常量，消除了这一隐患，同时减少了 Halstead 操作数。

## 修改点清单

| # | 文件位置 | 修改类型 | 说明 |
|---|---------|---------|------|
| 1 | 全局 | 重构 | 消除全局变量 `user_db/order_db/product_db/system_log/current_login_user`，用 `Database` 类封装 |
| 2 | 全局 | 重构 | 消除 `get_now()` 小工具，直接调用 `datetime.now().strftime(...)` |
| 3 | Database | 新增 | `prepare_order_products()`：一次性完成商品查找+库存检查+价格计算 |
| 4 | Database | 新增 | `restore_stock()`：取消订单时返还库存，消除重复遍历 |
| 5 | Database | 新增 | `deduct_stock()`：扣减库存，替代原 `create_order` 中的第三次循环 |
| 6 | 新增 | 新增 | `Result` 类：结构化返回值替代 `print` 语句 |
| 7 | 新增 | 新增 | `calc_discount()`：独立纯函数替代折扣计算的硬编码 if 链 |
| 8 | OrderService | 重构 | `create_order`：调用 `prepare_order_products()` 将三次循环降为一次 |
| 9 | OrderService | 重构 | `cancel_order`：调用 `restore_stock()` 消除与 `create_order` 重复的遍历逻辑 |
| 10 | OrderService | 重构 | `ship_order`+`complete_order`：合并入 `_advance_order()` helper |
| 11 | 全局 | 重构 | 订单状态从字符串 "0"/"1"/... 改为整数常量 S.PENDING/S.PAID/... |
| 12 | 全局 | 重构 | `discount_config` 字典改名为 `DISCOUNT_CFG` 元组常量 |

## 剩余局限性
- MI 仍然偏低（35.5），主要受 Halstead volume 制约（业务逻辑固有复杂度高，字典/列表字面量多）
- 重复代码率 8.1% 处于中等水平（<5% 为优秀），进一步削减会损害可读性
- LOC 259 已接近此功能集的最低合理值
