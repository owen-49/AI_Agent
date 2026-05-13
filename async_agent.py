import json
import re
import random
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from core.config import Config
from core.prompts import SYSTEM_PROMPT, PROBLEM_PROMPT_TEMPLATE, CONSTRUCTION_PROTOCOLS, REFLECTION_PROMPT
from core.engine import MathEngine


class AsyncHigherAlgebraProfessorAgent:
    """异步版 Agent：ReAct 状态机的 LLM 调用全部使用 ainvoke，支持并发"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            openai_api_key=Config.API_KEY,
            openai_api_base="https://api.openai.com/v1",
            temperature=Config.TEMPERATURE,
            max_retries=3,
        )
        self.engine = MathEngine()
        self.max_loop = 3

    # ── 工具方法（无 I/O，同步即可）──────────────────────────────────────

    def _generate_random_seeds(self, difficulty):
        random.seed(time.time_ns())

        matrix_sizes = [2, 2, 3, 3, 3, 4]
        size = random.choice(matrix_sizes)

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
            "综合题：融合多个知识点的综合性题目",
        ]
        problem_type = random.choice(problem_types)
        protocol = random.choice(CONSTRUCTION_PROTOCOLS)

        return {
            "matrix_size": size,
            "eigen_min": eigen_min,
            "eigen_max": eigen_max,
            "problem_type": problem_type,
            "protocol": protocol,
        }

    def _extract_json(self, text):
        try:
            json_str = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if json_str:
                return json.loads(json_str.group(1))
            return json.loads(text)
        except Exception as e:
            print(f"  [JSON解析异常] {e}")
            return None

    def _build_initial_prompt(self, topic, difficulty, seeds):
        formatted_protocol = seeds["protocol"].format(
            size=seeds["matrix_size"],
            eigen_min=seeds["eigen_min"],
            eigen_max=seeds["eigen_max"],
        )
        return PROBLEM_PROMPT_TEMPLATE.format(
            topic=topic,
            difficulty=difficulty,
            construction_protocol=formatted_protocol,
            matrix_size=seeds["matrix_size"],
            eigen_min=seeds["eigen_min"],
            eigen_max=seeds["eigen_max"],
            problem_type=seeds["problem_type"],
        )

    def _build_reflection_prompt(self, observation):
        return REFLECTION_PROMPT.format(observation=observation)

    # ── 核心异步方法 ────────────────────────────────────────────────────

    async def generate_verified_problem(self, topic, difficulty):
        """异步 ReAct 状态机：Reasoning → Acting → Observing → (Reflection → ...) → Done"""
        seeds = self._generate_random_seeds(difficulty)

        print(
            f"[Async] 启动: topic={topic[:20]}... diff={difficulty} "
            f"size={seeds['matrix_size']} eigen=[{seeds['eigen_min']},{seeds['eigen_max']}]"
        )

        initial_prompt = self._build_initial_prompt(topic, difficulty, seeds)

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=initial_prompt),
        ]

        for attempt in range(self.max_loop):
            state_label = "REASONING+ACTING" if attempt == 0 else "REFLECTING→REASONING+ACTING"

            # ── Phase 1+2: 异步 REASONING + ACTING ──
            response = await self.llm.ainvoke(messages)
            data = self._extract_json(response.content)

            if not data:
                observation = (
                    "JSON 格式解析失败。请确保："
                    "1) 输出包含在 ```json ... ``` 代码块中；"
                    "2) 所有必需字段完整：reasoning, title, topic, difficulty, latex_statement, sympy_script, analytical_solution。"
                )
                messages.append(AIMessage(content=response.content))
                messages.append(HumanMessage(content=self._build_reflection_prompt(observation)))
                continue

            reasoning = data.get("reasoning", "")
            print(f"  [{state_label} #{attempt+1}] {reasoning[:120]}...")

            # ── Phase 3: OBSERVING（同步，毫秒级）──
            is_valid, math_res = self.engine.verify_logic(data["sympy_script"])

            if is_valid:
                eigenvals = math_res.get("eigenvalues", {})
                if isinstance(eigenvals, dict):
                    eigen_vals = list(eigenvals.keys())
                else:
                    eigen_vals = list(eigenvals)
                is_elegant = all(val.is_integer for val in eigen_vals if val.is_real)

                if is_elegant:
                    print(f"  [DONE] ✅ 特征值: {eigen_vals}")
                    return data
                else:
                    observation = (
                        f"验证脚本执行成功，但特征值包含无理数。"
                        f"当前特征值: {eigen_vals}。"
                        f"请调整初始向量选取或特征值参数，确保所有特征值均为整数。"
                    )
            else:
                observation = f"SymPy 验证脚本执行错误: {math_res}"

            print(f"  [OBSERVATION] ❌ {str(observation)[:120]}")

            # ── Phase 4: REFLECTION → 下一轮迭代 ──
            messages.append(AIMessage(content=response.content))
            messages.append(HumanMessage(content=self._build_reflection_prompt(observation)))

        print(f"  [FAILED] ❌ 超过最大迭代次数 {self.max_loop}")
        return None
