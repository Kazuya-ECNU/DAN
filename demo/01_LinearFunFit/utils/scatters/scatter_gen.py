import numpy as np
import pandas as pd
import os

def generate_linear_scatter(
    n_samples=100,
    x_min=0,
    x_max=10,
    a=2,        # 斜率
    b=3,        # 截距
    noise=1.5,  # 噪声标准差
    seed=42,
    save_path="linear_scatter.csv"
):
    """
    生成带噪声的线性散点，并保存为 CSV
    返回：x, y (numpy array)
    """
    np.random.seed(seed)
    x = np.linspace(x_min, x_max, n_samples)
    y = a * x + b + np.random.normal(0, noise, size=n_samples)
    
    # 保存
    df = pd.DataFrame({"x": x, "y": y})
    df.to_csv(save_path, index=False)
    print(f"已保存到：{os.path.abspath(save_path)}")
    
    return x, y

# ------------------- 示例使用 -------------------
if __name__ == "__main__":
    # 生成
    x_gen, y_gen = generate_linear_scatter(
        n_samples=200,
        x_min=-5,
        x_max=15,
        a=1.2776,
        b=2.55567,
        noise=1.0,
        save_path="my_scatter.csv"
    )