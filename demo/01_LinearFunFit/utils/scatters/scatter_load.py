import numpy as np
import pandas as pd
import os

def load_linear_scatter(file_path="linear_scatter.csv"):
    """
    读取保存的散点文件
    返回：x, y (numpy array)
    """
    df = pd.read_csv(file_path)
    x = df["x"].values
    y = df["y"].values
    return x, y


# ------------------- 示例使用 -------------------
if __name__ == "__main__":
    # 读取
    x_load, y_load = load_linear_scatter("my_scatter.csv")

    # 画图验证
    import matplotlib.pyplot as plt
    plt.scatter(x_load, y_load, s=15, alpha=0.7)
    plt.plot(x_load, 1.8*x_load + 2.5, 'r-', lw=2, label='y=1.8x+2.5')
    plt.xlabel("x")
    plt.ylabel("y")
    plt.legend()
    plt.grid(True)
    plt.savefig('scatter.png')