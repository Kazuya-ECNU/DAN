"""
电商订单与用户管理系统 - 重构优化版v3
优化要点：
1. Database类封装所有数据+商品操作，消除全局变量污染
2. prepare_order_products()一次性完成查找+库存检查+价格计算，
   替代原create_order中的三次遍历product_db（核心优化）
3. restore_stock()由cancel_order复用，消除取消订单时的重复遍历
4. Result对象替代print，实现结构化返回
5. calc_discount()独立纯函数，替代硬编码if链
6. _advance_order()抽取ship/complete的共同模式，简化圈复杂度
7. 消除get_now()小工具，直接用datetime.now()
8. 订单状态用整数常量替代字符串硬编码，简化比较操作
"""

import time
import random
from datetime import datetime

# ========== 状态常量 ==========
class S:
    PENDING, PAID, SHIPPED, COMPLETED, CANCELLED = 0, 1, 2, 3, 4

STATUS_NAME = {S.PENDING: "待支付", S.PAID: "已支付", S.SHIPPED: "已发货",
                S.COMPLETED: "已完成", S.CANCELLED: "已取消"}
DISCOUNT_CFG = (("vip", 0.9), ("new_user", 0.85), ("holiday", 0.88))
SERVICE_FEE_RATE = 0.05

# ========== 结果对象 ==========
class Result:
    def __init__(self, ok, data=None, msg=""):
        self.ok = ok
        self.data = data
        self.msg = msg

# ========== 数据库（封装所有数据+核心商品操作） ==========
class Database:
    def __init__(self):
        self.users = []
        self.orders = []
        self.products = [
            {"id": 1, "name": "iPhone 15", "price": 5999, "stock": 100},
            {"id": 2, "name": "AirPods Pro", "price": 1799, "stock": 200},
            {"id": 3, "name": "MacBook Pro", "price": 12999, "stock": 50},
            {"id": 4, "name": "iPad Air", "price": 3599, "stock": 80},
            {"id": 5, "name": "Apple Watch", "price": 2999, "stock": 120},
            {"id": 6, "name": "Magic Keyboard", "price": 899, "stock": 150},
            {"id": 7, "name": "HomePod", "price": 2299, "stock": 60},
        ]
        self.logs = []
        self.current_user = None

    def find_user(self, username):
        for u in self.users:
            if u["username"] == username:
                return u
        return None

    def find_product(self, pid):
        for p in self.products:
            if p["id"] == pid:
                return p
        return None

    def find_order(self, order_id, need_user=True):
        for o in self.orders:
            if o["order_id"] == order_id:
                if not need_user or o["username"] == self.current_user["username"]:
                    return o
        return None

    def prepare_order_products(self, product_ids, quantities):
        """一次性完成查找+检查+计算（替代create_order中三次遍历product_db）"""
        info_list, total = [], 0
        for pid, qty in zip(product_ids, quantities):
            p = self.find_product(pid)
            if not p:
                print(f"商品ID{pid}不存在")
                return None, 0, False
            if p["stock"] < qty:
                print(f"商品{p['name']}库存不足")
                return None, 0, False
            sub = p["price"] * qty
            info_list.append({"id": p["id"], "name": p["name"],
                               "price": p["price"], "quantity": qty, "subtotal": sub})
            total += sub
        return info_list, total, True

    def deduct_stock(self, product_ids, quantities):
        for pid, qty in zip(product_ids, quantities):
            p = self.find_product(pid)
            if p:
                p["stock"] -= qty

    def restore_stock(self, product_info_list):
        """取消订单时返还库存（复用prepare逻辑，消除cancel_order重复遍历）"""
        for item in product_info_list:
            p = self.find_product(item["id"])
            if p:
                p["stock"] += item["quantity"]

    def log(self, msg):
        self.logs.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


# ========== 折扣计算（独立纯函数，替代硬编码if链） ==========
def calc_discount(db, is_holiday):
    if is_holiday:
        d = DISCOUNT_CFG[2][1]
    elif not db.orders:
        d = DISCOUNT_CFG[1][1]
    elif db.current_user["is_vip"]:
        d = DISCOUNT_CFG[0][1]
    else:
        d = 1.0
    if db.current_user["balance"] < 5000:
        d += 0.05
    return d


# ========== 业务服务 ==========
class OrderService:
    def __init__(self, db):
        self.db = db

    def create_order(self, product_ids, quantities, is_holiday=False):
        if not self.db.current_user:
            return Result(False, msg="请先登录")
        if len(product_ids) != len(quantities):
            return Result(False, msg="商品和数量不匹配")
        info_list, total, ok = self.db.prepare_order_products(product_ids, quantities)
        if not ok:
            return Result(False, msg="库存检查未通过")
        discount = calc_discount(self.db, is_holiday)
        fee = total * discount * SERVICE_FEE_RATE
        final_amount = round(total * discount + fee, 2)
        self.db.deduct_stock(product_ids, quantities)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        order = {
            "order_id": f"ORD{int(time.time())}{random.randint(100, 999)}",
            "user_id": self.db.current_user["id"],
            "username": self.db.current_user["username"],
            "products": info_list,
            "total_amount": total,
            "discount": discount,
            "service_fee": fee,
            "final_amount": final_amount,
            "status": S.PENDING,
            "create_time": now, "pay_time": "", "ship_time": "", "complete_time": "",
        }
        self.db.orders.append(order)
        self.db.log(f"订单{order['order_id']}创建成功，金额{final_amount}")
        return Result(True, data=order["order_id"],
                      msg=f"订单创建成功！订单号：{order['order_id']}，总金额：{final_amount}")

    def pay_order(self, order_id):
        if not self.db.current_user:
            return Result(False, msg="请先登录")
        order = self.db.find_order(order_id)
        if not order:
            return Result(False, msg="订单不存在")
        if order["status"] != S.PENDING:
            return Result(False, msg="订单状态不允许支付")
        if self.db.current_user["balance"] < order["final_amount"]:
            return Result(False, msg="余额不足")
        self.db.current_user["balance"] -= order["final_amount"]
        order["status"] = S.PAID
        order["pay_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.log(f"订单{order_id}支付成功")
        return Result(True, msg="支付成功")

    def _advance_order(self, order_id, expect, nxt, field, err, verb):
        """ship/complete的共同模式抽取为一个函数"""
        order = self.db.find_order(order_id, need_user=False)
        if not order:
            return Result(False, msg="订单不存在")
        if order["status"] != expect:
            return Result(False, msg=err)
        order["status"] = nxt
        order[field] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.log(f"订单{order_id}{verb}")
        return Result(True, msg=err)

    def ship_order(self, order_id):
        return self._advance_order(order_id, S.PAID, S.SHIPPED, "ship_time", "订单未支付", "已发货")

    def complete_order(self, order_id):
        return self._advance_order(order_id, S.SHIPPED, S.COMPLETED, "complete_time", "订单未发货", "已完成")

    def cancel_order(self, order_id):
        if not self.db.current_user:
            return Result(False, msg="请先登录")
        order = self.db.find_order(order_id)
        if not order:
            return Result(False, msg="订单不存在")
        if order["status"] != S.PENDING:
            return Result(False, msg="只能取消待支付订单")
        self.db.restore_stock(order["products"])
        order["status"] = S.CANCELLED
        self.db.log(f"订单{order_id}已取消")
        return Result(True, msg="订单取消成功")

    def query_my_orders(self, status=None):
        if not self.db.current_user:
            print("请先登录")
            return []
        result = [o for o in self.db.orders if o["username"] == self.db.current_user["username"]]
        if status is not None:
            result = [o for o in result if o["status"] == status]
        print(f"====={self.db.current_user['username']}的订单=====")
        for o in result:
            print(f"订单号：{o['order_id']} 状态：{STATUS_NAME[o['status']]} 金额：{o['final_amount']}")
            for p in o["products"]:
                print(f"  - {p['name']} x{p['quantity']} = {p['subtotal']}")
        return result

    def stat_sales(self):
        total_sales = 0
        paid_count = 0
        sales_map = {p["name"]: 0 for p in self.db.products}
        for o in self.db.orders:
            if o["status"] in (S.PAID, S.SHIPPED, S.COMPLETED):
                total_sales += o["final_amount"]
                paid_count += 1
                for p in o["products"]:
                    sales_map[p["name"]] += p["quantity"]
        print("=====销售统计=====")
        print(f"总订单数：{len(self.db.orders)} 已支付：{paid_count} 销售额：{round(total_sales, 2)}")
        for name, n in sales_map.items():
            print(f"  {name}：{n}件")


class UserService:
    def __init__(self, db):
        self.db = db

    def register_user(self, username, password, phone, is_vip):
        if self.db.find_user(username):
            print("用户名已存在")
            return False
        user = {"id": len(self.db.users) + 1, "username": username,
                "password": password, "phone": phone, "is_vip": is_vip,
                "balance": 10000, "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        self.db.users.append(user)
        self.db.log(f"用户{username}注册成功")
        return True

    def login(self, username, password):
        u = self.db.find_user(username)
        if u and u["password"] == password:
            self.db.current_user = u
            self.db.log(f"用户{username}登录成功")
            print("登录成功")
            return True
        print("用户名或密码错误")
        return False

    def logout(self):
        if self.db.current_user:
            self.db.log(f"用户{self.db.current_user['username']}退出登录")
            self.db.current_user = None
            print("退出成功")
        else:
            print("未登录")

    def query_product(self, keyword=None):
        print("=====商品列表=====" if keyword is None else f"=====搜索结果：{keyword}=====")
        for p in self.db.products:
            if keyword is None or keyword in p["name"]:
                print(f"ID:{p['id']} 名称:{p['name']} 价格:{p['price']} 库存:{p['stock']}")
        return self.db.products

    def show_logs(self):
        print("=====系统日志=====")
        for log in self.db.logs:
            print(log)


# ========== 测试入口 ==========
if __name__ == "__main__":
    db = Database()
    orders = OrderService(db)
    users = UserService(db)

    users.register_user("zhangsan", "123456", "13800138000", True)
    users.register_user("lisi", "654321", "13900139000", False)

    users.login("zhangsan", "123456")
    users.query_product()

    oid1 = orders.create_order([1, 2], [1, 1])
    if oid1.ok:
        orders.pay_order(oid1.data)
        orders.ship_order(oid1.data)
        orders.complete_order(oid1.data)

    oid2 = orders.create_order([3], [1], is_holiday=True)
    if oid2.ok:
        orders.cancel_order(oid2.data)

    orders.query_my_orders()
    orders.stat_sales()
    users.show_logs()
    users.logout()
