import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from core.config import Config
from core.prompts import SYSTEM_PROMPT, PROBLEM_PROMPT_TEMPLATE
from core.engine import MathEngine

class HigherAlgebraProfessorAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            openai_api_key=Config.API_KEY,
            openai_api_base="https://api.openai.com/v1", 
            temperature=0.3, 
            max_retries=3
        )
        self.engine = MathEngine()
        self.max_loop = 3 

    def _extract_json(self, text):
        try:
            json_str = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if json_str:
                return json.loads(json_str.group(1))
            return json.loads(text)
        except Exception as e:
            print(f"解析异常: {e}")
            return None

    def generate_verified_problem(self, topic, difficulty):
        current_feedback = ""
        
        for attempt in range(self.max_loop):
            print(f"\n[Iteration {attempt + 1}] 正在应用反向构造协议...")
            
            user_prompt = PROBLEM_PROMPT_TEMPLATE.format(topic=topic, difficulty=difficulty)
            if current_feedback:
                user_prompt += f"\n\n逻辑冲突警告：\n{current_feedback}"

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
                    print(f"成功生成数值优美的题目。特征值: {list(eigenvals.keys())}")
                    return data
                else:
                    current_feedback = "生成的矩阵特征值包含无理数，不符合'数值友好'要求。请重新通过 P*D*P^-1 构造。"
            else:
                current_feedback = f"代码运行错误: {math_res}"
        
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