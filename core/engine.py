import multiprocessing


def _run_sympy_script(script: str, result_queue):
    """在隔离子进程中执行 SymPy 验证脚本（模块级函数，兼容 Windows spawn）"""
    import sympy
    import numpy as np

    safe_globals = {
        # ── 模块入口 ──
        "sympy": sympy,
        "np": np,
        # ── 核心构造器 ──
        "Matrix": sympy.Matrix,
        "symbols": sympy.symbols,
        "diag": sympy.diag,
        "eye": sympy.eye,
        "zeros": sympy.zeros,
        "ones": sympy.ones,
        # ── 矩阵运算 ──
        "det": lambda m: m.det(),
        "trace": lambda m: m.trace(),
        "rank": lambda m: m.rank(),
        "rref": lambda m: m.rref(),
        "eigenvals": lambda m: m.eigenvals(),
        "eigenvects": lambda m: m.eigenvects(),
        "transpose": lambda m: m.T,
        "diagonalize": lambda m: m.diagonalize(),
        "GramSchmidt": sympy.matrices.GramSchmidt,
        "is_symmetric": lambda m: m == m.T,
        # ── 符号运算 ──
        "simplify": sympy.simplify,
        "solve": sympy.solve,
        "factor": sympy.factor,
        "expand": sympy.expand,
        "Eq": sympy.Eq,
        # ── 类型与常量 ──
        "Rational": sympy.Rational,
        "Integer": sympy.Integer,
        "sqrt": sympy.sqrt,
        "I": sympy.I,
        "pi": sympy.pi,
        "Abs": sympy.Abs,
    }

    try:
        local_env = {}
        exec(script, safe_globals, local_env)

        if "result" not in local_env:
            result_queue.put(("invalid", "脚本运行成功但未定义变量 'result'"))
            return

        try:
            result_queue.put(("success", local_env["result"]))
        except Exception:
            result_queue.put(("success", {"raw_output": str(local_env["result"])}))
    except Exception as e:
        result_queue.put(("error", f"{type(e).__name__}: {str(e)}"))


class MathEngine:
    DEFAULT_TIMEOUT = 10

    @staticmethod
    def verify_logic(script: str, timeout: int = None):
        if timeout is None:
            timeout = MathEngine.DEFAULT_TIMEOUT

        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()

        process = ctx.Process(
            target=_run_sympy_script,
            args=(script, result_queue),
        )

        process.start()
        process.join(timeout=timeout)

        if process.is_alive():
            process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join()
            return False, f"执行超时（>{timeout}秒），脚本可能包含死循环、无限递归或运算量过大的操作"

        if result_queue.empty():
            return False, "子进程异常退出，未返回任何结果"

        try:
            status, data = result_queue.get(block=False)
        except Exception:
            return False, "无法从子进程读取执行结果"

        if status == "success":
            return True, data
        else:
            return False, data
