# 电商订单与用户管理系统（隐性烂代码：高耦合、无封装、全局污染、重复逻辑）
import time
import random
from datetime import datetime

# 全局"数据库"（无封装，所有函数直接读写）
user_db = []
order_db = []
product_db = [
    {"id": 1, "name": "iPhone 15", "price": 5999, "stock": 100},
    {"id": 2, "name": "AirPods Pro", "price": 1799, "stock": 200},
    {"id": 3, "name": "MacBook Pro", "price": 12999, "stock": 50},
    {"id": 4, "name": "iPad Air", "price": 3599, "stock": 80},
    {"id": 5, "name": "Apple Watch", "price": 2999, "stock": 120},
    {"id": 6, "name": "Magic Keyboard", "price": 899, "stock": 150},
    {"id": 7, "name": "HomePod", "price": 2299, "stock": 60}
]
discount_config = {"vip": 0.9, "new_user": 0.85, "holiday": 0.88}
order_status_map = {"0": "待支付", "1": "已支付", "2": "已发货", "3": "已完成", "4": "已取消"}
system_log = []
current_login_user = None
service_fee_rate = 0.05

# 用户注册（无输入验证，直接写全局）
def register_user(username, password, phone, is_vip):
    global user_db
    for u in user_db:
        if u["username"] == username:
            print("用户名已存在")
            return False
    user_id = len(user_db) + 1
    create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = {
        "id": user_id,
        "username": username,
        "password": password,
        "phone": phone,
        "is_vip": is_vip,
        "balance": 10000,
        "create_time": create_time
    }
    user_db.append(user)
    system_log.append(f"[{create_time}] 用户{username}注册成功")
    return True

# 用户登录（明文密码，无加密）
def login(username, password):
    global current_login_user
    for u in user_db:
        if u["username"] == username and u["password"] == password:
            current_login_user = u
            system_log.append(f"[{get_now()}] 用户{username}登录成功")
            print("登录成功")
            return True
    print("用户名或密码错误")
    return False

# 退出登录
def logout():
    global current_login_user
    if current_login_user:
        system_log.append(f"[{get_now()}] 用户{current_login_user['username']}退出登录")
        current_login_user = None
        print("退出成功")
    else:
        print("未登录")

# 获取当前时间（小工具，但被到处调用）
def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 查询商品（硬编码打印，无返回结构化数据）
def query_product(keyword=None):
    if keyword is None:
        print("=====商品列表=====")
        for p in product_db:
            print(f"ID:{p['id']} 名称:{p['name']} 价格:{p['price']} 库存:{p['stock']}")
    else:
        print(f"=====搜索结果：{keyword}=====")
        for p in product_db:
            if keyword in p["name"]:
                print(f"ID:{p['id']} 名称:{p['name']} 价格:{p['price']} 库存:{p['stock']}")
    return product_db

# 核心：创建订单（长函数、高耦合、无事务、重复循环）
def create_order(product_ids, quantities, is_holiday=False):
    global current_login_user, order_db, product_db
    if current_login_user is None:
        print("请先登录")
        return None
    if len(product_ids) != len(quantities):
        print("商品和数量不匹配")
        return None
    
    total_amount = 0
    product_info_list = []
    stock_check_result = True
    
    # 第一次循环：检查库存（重复遍历商品列表）
    for i in range(len(product_ids)):
        pid = product_ids[i]
        qty = quantities[i]
        find = False
        for p in product_db:
            if p["id"] == pid:
                find = True
                if p["stock"] < qty:
                    print(f"商品{p['name']}库存不足")
                    stock_check_result = False
                break
        if not find:
            print(f"商品ID{pid}不存在")
            stock_check_result = False
    
    if not stock_check_result:
        return None
    
    # 第二次循环：计算总价（又遍历了一遍商品列表，重复代码）
    for i in range(len(product_ids)):
        pid = product_ids[i]
        qty = quantities[i]
        for p in product_db:
            if p["id"] == pid:
                subtotal = p["price"] * qty
                total_amount += subtotal
                product_info_list.append({
                    "name": p["name"], "price": p["price"], 
                    "quantity": qty, "subtotal": subtotal
                })
                break
    
    # 折扣计算（硬编码规则，耦合用户、订单全局状态）
    discount = 1.0
    if current_login_user["is_vip"]:
        discount = discount_config["vip"]
    if len(order_db) == 0:
        discount = discount_config["new_user"]
    if is_holiday:
        discount = discount_config["holiday"]
    if current_login_user["balance"] < 5000:
        discount = discount + 0.05
    
    final_amount = total_amount * discount
    service_fee = final_amount * service_fee_rate
    final_amount = final_amount + service_fee
    final_amount = round(final_amount, 2)
    
    # 第三次循环：扣减库存（第三次遍历商品列表，完全重复）
    for i in range(len(product_ids)):
        pid = product_ids[i]
        qty = quantities[i]
        for p in product_db:
            if p["id"] == pid:
                p["stock"] -= qty
                break
    
    # 生成订单（硬编码字段，无模型）
    order_id = "ORD" + str(int(time.time())) + str(random.randint(100, 999))
    create_time = get_now()
    order = {
        "order_id": order_id,
        "user_id": current_login_user["id"],
        "username": current_login_user["username"],
        "products": product_info_list,
        "total_amount": total_amount,
        "discount": discount,
        "service_fee": service_fee,
        "final_amount": final_amount,
        "status": "0",
        "create_time": create_time,
        "pay_time": "",
        "ship_time": "",
        "complete_time": ""
    }
    order_db.append(order)
    system_log.append(f"[{create_time}] 订单{order_id}创建成功，金额{final_amount}")
    print(f"订单创建成功！订单号：{order_id}，总金额：{final_amount}")
    return order_id

# 支付订单（耦合全局用户余额）
def pay_order(order_id):
    global current_login_user, order_db
    if current_login_user is None:
        print("请先登录")
        return False
    order = None
    for o in order_db:
        if o["order_id"] == order_id and o["username"] == current_login_user["username"]:
            order = o
            break
    if order is None:
        print("订单不存在")
        return False
    if order["status"] != "0":
        print("订单状态不允许支付")
        return False
    if current_login_user["balance"] < order["final_amount"]:
        print("余额不足")
        return False
    
    current_login_user["balance"] -= order["final_amount"]
    order["status"] = "1"
    order["pay_time"] = get_now()
    system_log.append(f"[{get_now()}] 订单{order_id}支付成功")
    print("支付成功")
    return True

# 发货（无权限校验，任何人都能发任意订单）
def ship_order(order_id):
    for o in order_db:
        if o["order_id"] == order_id:
            if o["status"] == "1":
                o["status"] = "2"
                o["ship_time"] = get_now()
                system_log.append(f"[{get_now()}] 订单{order_id}已发货")
                print("发货成功")
                return True
            else:
                print("订单未支付")
                return False
    print("订单不存在")
    return False

# 完成订单
def complete_order(order_id):
    for o in order_db:
        if o["order_id"] == order_id:
            if o["status"] == "2":
                o["status"] = "3"
                o["complete_time"] = get_now()
                system_log.append(f"[{get_now()}] 订单{order_id}已完成")
                print("订单完成")
                return True
            else:
                print("订单未发货")
                return False
    print("订单不存在")
    return False

# 取消订单（重复的库存返还逻辑）
def cancel_order(order_id):
    global current_login_user, product_db
    if current_login_user is None:
        print("请先登录")
        return False
    order = None
    for o in order_db:
        if o["order_id"] == order_id and o["username"] == current_login_user["username"]:
            order = o
            break
    if order is None:
        print("订单不存在")
        return False
    if order["status"] != "0":
        print("只能取消待支付订单")
        return False
    
    # 返还库存（又遍历了一遍商品列表，和创建订单的扣库存逻辑完全重复）
    for p_info in order["products"]:
        p_name = p_info["name"]
        qty = p_info["quantity"]
        for p in product_db:
            if p["name"] == p_name:
                p["stock"] += qty
                break
    
    order["status"] = "4"
    system_log.append(f"[{get_now()}] 订单{order_id}已取消")
    print("订单取消成功")
    return True

# 查询我的订单（硬编码打印，无复用）
def query_my_orders(status=None):
    global current_login_user
    if current_login_user is None:
        print("请先登录")
        return []
    print(f"====={current_login_user['username']}的订单=====")
    for o in order_db:
        if o["username"] == current_login_user["username"]:
            if status is not None and o["status"] != status:
                continue
            status_str = order_status_map[o["status"]]
            print(f"订单号：{o['order_id']}")
            print(f"状态：{status_str}")
            print(f"创建时间：{o['create_time']}")
            print(f"总金额：{o['final_amount']}")
            print("商品：")
            for p in o["products"]:
                print(f"- {p['name']} x{p['quantity']} = {p['subtotal']}")
            print("-" * 30)
    return [o for o in order_db if o["username"] == current_login_user["username"]]

# 查看系统日志
def show_logs():
    print("=====系统日志=====")
    for log in system_log:
        print(log)

# 销售统计（耦合所有全局数据）
def stat_sales():
    total_sales = 0
    total_orders = len(order_db)
    paid_orders = 0
    product_sales = {}
    for p in product_db:
        product_sales[p["name"]] = 0
    
    for o in order_db:
        if o["status"] in ["1", "2", "3"]:
            total_sales += o["final_amount"]
            paid_orders += 1
            for p_info in o["products"]:
                p_name = p_info["name"]
                product_sales[p_name] += p_info["quantity"]
    
    print("=====销售统计=====")
    print(f"总订单数：{total_orders}")
    print(f"已支付订单：{paid_orders}")
    print(f"总销售额：{round(total_sales, 2)}")
    print("商品销量：")
    for name, sales in product_sales.items():
        print(f"{name}：{sales}件")

# 测试入口
if __name__ == "__main__":
    register_user("zhangsan", "123456", "13800138000", True)
    register_user("lisi", "654321", "13900139000", False)
    
    login("zhangsan", "123456")
    query_product()
    
    oid1 = create_order([1, 2], [1, 1])
    pay_order(oid1)
    ship_order(oid1)
    complete_order(oid1)
    
    oid2 = create_order([3], [1], is_holiday=True)
    cancel_order(oid2)
    
    query_my_orders()
    stat_sales()
    show_logs()
    logout()