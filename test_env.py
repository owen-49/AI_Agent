import sympy
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# 验证 SymPy 是否工作
x = sympy.symbols('x')
expr = sympy.expand((x + 1)**2)
print(f"SymPy 验证: (x+1)^2 = {expr}")

# 验证 API 配置
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print("✅ 环境配置成功：API Key 已加载")
else:
    print("❌ 警告：未检测到 API Key，请检查 .env 文件")