import json
import re
import random
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import Config
from core.prompts import SYSTEM_PROMPT, PROBLEM_PROMPT_TEMPLATE, CONSTRUCTION_PROTOCOLS
from core.engine import MathEngine

class HigherAlgebraProfessorAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            openai_api_key=Config.API_KEY,
            openai_api_base="https://api.openai.com/v1",
            temperature=Config.TEMPERATURE,
            max_retries=3
        )
        self.engine = MathEngine()
        self.max_loop = 3

    def _generate_random_seeds(self, difficulty):
        """每次生成题目时注入不同的随机种子参数"""
        random.seed(time.time_ns())

        matrix_sizes = [2, 2, 3, 3, 3, 4]  # 加权分布：2x2 和 4x4 较少，3x3 较多
        size = random.choice(matrix_sizes)

        # 根据难度调整特征值范围
        if difficulty <= 2:
            eigen_min, eigen_max = -3, 5
        elif difficulty <= 4:
            eigen_min, eigen_max = -5, 10
        else:
            eigen_min, eigen_max = -10, 20

        problem_types = [
            "计算题：要求学生进行具体的矩阵运算",
            "证明题：要求学生证明某个数学性质",
            "应用题：将矩阵理论与实际场景结合",
            "分析题：要求学生分析矩阵的结构性质",
            "综合题：融合多个知识点的综合性题目"
        ]
        problem_type = random.choice(problem_types)

        protocol = random.choice(CONSTRUCTION_PROTOCOLS)

        return {
            "matrix_size": size,
            "eigen_min": eigen_min,
            "eigen_max": eigen_max,
            "problem_type": problem_type,
            "protocol": protocol
        }

    def _extract_json(self, text):
        try:
            json_str = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if json_str:
                return json.loads(json_str.group(1))
            return json.loads(text)
        except Exception as e:
            print(f"解析异常: {e}")
            return None

    def _build_prompt(self, topic, difficulty, seeds, feedback=""):
        """根据种子和反馈构建完整的 prompt"""
        formatted_protocol = seeds["protocol"].format(
            size=seeds["matrix_size"],
            eigen_min=seeds["eigen_min"],
            eigen_max=seeds["eigen_max"]
        )
        prompt = PROBLEM_PROMPT_TEMPLATE.format(
            topic=topic,
            difficulty=difficulty,
            construction_protocol=formatted_protocol,
            matrix_size=seeds["matrix_size"],
            eigen_min=seeds["eigen_min"],
            eigen_max=seeds["eigen_max"],
            problem_type=seeds["problem_type"]
        )
        if feedback:
            prompt += f"\n\n【上轮验证反馈】\n{feedback}\n请使用全新的随机参数重新生成，确保与上一轮题目不同。"
        return prompt

    def generate_verified_problem(self, topic, difficulty):
        current_feedback = ""

        for attempt in range(self.max_loop):
            seeds = self._generate_random_seeds(difficulty)
            print(f"\n[Iteration {attempt + 1}] 正在应用反向构造协议...")
            print(f"  随机种子: size={seeds['matrix_size']}, eigen_range=[{seeds['eigen_min']},{seeds['eigen_max']}], type={seeds['problem_type']}")

            user_prompt = self._build_prompt(topic, difficulty, seeds, current_feedback)

            response = self.llm.invoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ])

            data = self._extract_json(response.content)
            if not data: continue

            is_valid, math_res = self.engine.verify_logic(data["sympy_script"])

            if is_valid:
                eigenvals = math_res.get('eigenvalues', {})
                if isinstance(eigenvals, dict):
                    eigen_vals = list(eigenvals.keys())
                else:
                    eigen_vals = list(eigenvals)
                is_elegant = all(val.is_integer for val in eigen_vals if val.is_real)

                if is_elegant:
                    print(f"成功生成数值优美的题目。特征值: {eigen_vals}")
                    return data
                else:
                    current_feedback = "生成的矩阵特征值包含无理数，不符合'数值友好'要求。请重新构造，确保特征值均为整数。"
            else:
                current_feedback = f"SymPy 验证脚本执行错误: {math_res}。请修正 sympy_script。"

        return None

def display_output(data):
    if not data: return
    print("\n" + "═"*60)
    print(f"【课题】{data['title']} (难度: {data['difficulty']})")
    print(f"【知识点】{data['topic']}")
    print("-" * 60)
    print(f"【题干 (LaTeX)】:\n{data['latex_statement']}")
    print("-" * 60)
    print(f"【标准解题步骤】:\n{data['analytical_solution']}")
    print("═"*60 + "\n")

if __name__ == "__main__":
    prof_agent = HigherAlgebraProfessorAgent()

    topic_input = "实对称矩阵的特征值性质与对角化"
    problem_data = prof_agent.generate_verified_problem(topic_input, 4)

    if problem_data:
        display_output(problem_data)
