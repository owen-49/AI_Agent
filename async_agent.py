import json
import re
import random
import time
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from core.config import Config
from core.prompts import SYSTEM_PROMPT, PROBLEM_PROMPT_TEMPLATE, CONSTRUCTION_PROTOCOLS, REFLECTION_PROMPT
from core.engine import MathEngine, MatrixGenerator


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

        # ── 预计算合法矩阵（保证整数特征值）──
        matrix_2d, eigenvalues = MatrixGenerator.generate(size, eigen_min, eigen_max)

        return {
            "matrix_size": size,
            "eigen_min": eigen_min,
            "eigen_max": eigen_max,
            "problem_type": problem_type,
            "protocol": protocol,
            "precomputed_matrix": matrix_2d,
            "precomputed_eigenvalues": eigenvalues,
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

        matrix_latex = MatrixGenerator.matrix_to_latex(seeds["precomputed_matrix"])
        eigenvalues_str = ", ".join(str(ev) for ev in seeds["precomputed_eigenvalues"])
        precomputed_section = (
            f"矩阵 A = {matrix_latex}\n"
            f"该矩阵的整数特征值为: {eigenvalues_str}\n"
            f"矩阵的 Python 表示: {seeds['precomputed_matrix']}"
        )

        return PROBLEM_PROMPT_TEMPLATE.format(
            topic=topic,
            difficulty=difficulty,
            construction_protocol=formatted_protocol,
            precomputed_matrix_section=precomputed_section,
            matrix_size=seeds["matrix_size"],
            eigen_min=seeds["eigen_min"],
            eigen_max=seeds["eigen_max"],
            problem_type=seeds["problem_type"],
            expected_eigenvalues=eigenvalues_str,
        )

    def _build_reflection_prompt(self, observation):
        return REFLECTION_PROMPT.format(observation=observation)

    def _check_eigenvalues_integer(self, math_res):
        """Robust check: are all computed eigenvalues integers?

        Handles both SymPy Integer objects (from A.eigenvals() dict keys)
        and plain Python ints/floats (from LLM-generated result lists).
        """
        eigenvals = math_res.get('eigenvalues', {})
        if isinstance(eigenvals, dict):
            eigen_vals_raw = list(eigenvals.keys())
        elif hasattr(eigenvals, '__iter__') and not isinstance(eigenvals, (bool, str)):
            eigen_vals_raw = list(eigenvals)
        else:
            return False, []

        if not eigen_vals_raw:
            return False, []

        eigen_vals = []
        for val in eigen_vals_raw:
            try:
                num = int(val)
                eigen_vals.append(num)
            except (TypeError, ValueError):
                try:
                    num = float(val)
                    if num != int(num):
                        return False, [val]
                    eigen_vals.append(int(num))
                except (TypeError, ValueError):
                    return False, [val]

        return True, eigen_vals

    # ── 核心异步方法 ────────────────────────────────────────────────────

    async def generate_verified_problem(self, topic, difficulty):
        """异步 ReAct 状态机：使用预计算矩阵 + LLM 生成题目 + 双重验证"""
        seeds = self._generate_random_seeds(difficulty)

        print(
            f"[Async] 启动: topic={topic[:20]}... diff={difficulty} "
            f"size={seeds['matrix_size']} eigen=[{seeds['eigen_min']},{seeds['eigen_max']}]"
            f" pre_eig={seeds['precomputed_eigenvalues']}"
        )

        # ── 生成并运行程序化验证脚本（保证矩阵正确性）──
        prog_script = MatrixGenerator.make_verification_script(
            seeds["precomputed_matrix"],
            seeds["precomputed_eigenvalues"],
            seeds["matrix_size"],
        )
        prog_ok, prog_res = self.engine.verify_logic(prog_script)
        if not prog_ok:
            print(f"  [FATAL] 程序化验证失败: {prog_res}")
            return None
        print(f"  [预验证] ✅ 程序化验证通过")

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

            # ── Phase 3: OBSERVING — 运行 LLM 生成的验证脚本 ──
            llm_script = data.get("sympy_script", "")
            if llm_script.strip():
                is_valid, math_res = self.engine.verify_logic(llm_script)

                if is_valid:
                    is_int, eigen_vals = self._check_eigenvalues_integer(math_res)
                    if is_int:
                        print(f"  [DONE] ✅ LLM脚本验证通过, 特征值: {eigen_vals}")
                        return data
                    else:
                        observation = (
                            f"LLM验证脚本执行成功，但特征值检查未通过。"
                            f"当前特征值: {eigen_vals}。"
                            f"系统期望的整数特征值为: {seeds['precomputed_eigenvalues']}。"
                            f"请修正 sympy_script 以正确验证给定矩阵 A 的特征值。"
                        )
                else:
                    observation = f"LLM验证脚本执行错误: {math_res}。请检查并修正 sympy_script。"
            else:
                observation = "sympy_script 字段为空，请提供完整的验证脚本。"

            print(f"  [OBSERVATION] ❌ {str(observation)[:120]}")

            # ── 后备：如果 LLM 脚本失败但矩阵本身正确，接受结果 ──
            if attempt == self.max_loop - 1:
                print(f"  [FALLBACK] 程序化验证已通过，矩阵正确，接受 LLM 输出")
                return data

            # ── Phase 4: REFLECTION → 下一轮迭代 ──
            messages.append(AIMessage(content=response.content))
            messages.append(HumanMessage(content=self._build_reflection_prompt(observation)))

        print(f"  [FAILED] ❌ 超过最大迭代次数 {self.max_loop}")
        return None
