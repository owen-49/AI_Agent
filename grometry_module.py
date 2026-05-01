import os
import json
import random
import sympy as sp
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# 强制加载环境变量
load_dotenv()

class GeometryAgent:
    def __init__(self):
        # 调高 temperature 以增加题目多样性
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.8)
        
        self.prompt = PromptTemplate(
            input_variables=["topic"],
            template="""
            你是一位数学教授。请生成一道关于{topic}的解析几何题目。
            要求：
            1. 题目不能与常见的教材例题雷同，参数要随机。
            2. 输出必须是纯 JSON 格式，包含：
               - "problem": 题干文本(LaTeX)
               - "type": "ellipse" 或 "hyperbola" 或 "parabola"
               - "params": 字典，例如 {{"a": 5, "b": 3}}
               - "answer": 解题思路
            3. 不要包含任何 markdown 代码块标记，只输出 JSON。
            """
        )

    def generate_problem(self, topic="解析几何"):
        # 随机选择一个子话题，增加多样性
        topics = ["椭圆", "双曲线", "抛物线"]
        selected_topic = random.choice(topics)
        
        chain = self.prompt | self.llm
        response = chain.invoke({"topic": selected_topic})
        
        # 强力清理响应内容
        content = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)

    def render(self, data):
        shape = data.get('type')
        params = data['params']
        
        plt.figure(figsize=(6,6))
        
        if shape == 'ellipse':
            a, b = params['a'], params['b']
            c = np.sqrt(max(0, a**2 - b**2))
            t = np.linspace(0, 2*np.pi, 200)
            plt.plot(a*np.cos(t), b*np.sin(t), label=f'Ellipse a={a}, b={b}')
            plt.scatter([c, -c], [0, 0], color='red', label='Foci')
            
        elif shape == 'hyperbola':
            a, b = params['a'], params['b']
            c = np.sqrt(a**2 + b**2)
            t = np.linspace(-2, 2, 200)
            plt.plot(a*np.cosh(t), b*np.sinh(t), 'g', label='Hyperbola')
            plt.plot(-a*np.cosh(t), b*np.sinh(t), 'g')
            plt.scatter([c, -c], [0, 0], color='red')

        plt.title(f"Dynamic Generated: {shape}")
        plt.axis('equal')
        plt.grid(True)
        plt.legend()
        plt.show()

if __name__ == "__main__":
    agent = GeometryAgent()
    # 连续调用测试
    for i in range(2):
        print(f"\n--- 第 {i+1} 次出题 ---")
        data = agent.generate_problem("解析几何")
        print(f"题目: {data['problem']}")
        agent.render(data)