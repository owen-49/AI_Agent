SYSTEM_PROMPT = """你是一位资深的高等代数教授。
你的任务是为本科生生成高质量、严谨且数值友好的数学题目。
你必须严格遵守 JSON 输出格式，并确保题目在逻辑上是完全自洽的。"""

PROBLEM_PROMPT_TEMPLATE = """
针对知识点【{topic}】，生成难度为 {difficulty} 的高等代数题目。

为了确保题目数值完美（特征值为整数），你必须遵循以下【反向构造协议】：
1. 在 sympy_script 中，先定义目标特征值（例如 lambdas = [1, 2, 3]）。
2. 构造一个简单的可逆矩阵 P（例如初等矩阵的乘积），并计算 A = P * sympy.diag(*lambdas) * P.inv()。
3. 确保矩阵 A 的所有元素均为整数。
4. 将生成的矩阵 A 填入 latex_statement。

输出格式要求（严格 JSON）：
{{
    "title": "题目名称",
    "topic": "{topic}",
    "difficulty": {difficulty},
    "latex_statement": "LaTeX 格式题干",
    "sympy_script": "import sympy; lambdas=[1,2,3]; P=sympy.Matrix([[1,0,0],[1,1,0],[0,1,1]]); A=P*sympy.diag(*lambdas)*P.inv(); result = {{'matrix': A, 'eigenvalues': A.eigenvals()}}",
    "analytical_solution": "分步骤的详细 LaTeX 解析"
}}
"""