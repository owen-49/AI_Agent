import multiprocessing
import random


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


class MatrixGenerator:
    """Programmatic generator for symmetric matrices with integer eigenvalues.

    Uses guaranteed constructions (Pythagorean-triple parameterization for 2x2 blocks,
    block-diagonal composition, and permutation similarity) to produce matrices that
    always have integer entries and integer eigenvalues — avoiding the irrational
    numbers introduced by Gram-Schmidt orthogonalization.
    """

    @staticmethod
    def _pythagorean_triple():
        """Return (m, n) such that (m^2-n^2, 2mn, m^2+n^2) is a Pythagorean triple."""
        m = random.randint(2, 5)
        n = random.randint(1, m - 1)
        return m, n

    @staticmethod
    def _generate_2x2_block(eigen_min, eigen_max):
        """Generate a 2x2 symmetric integer matrix with distinct integer eigenvalues.

        Uses the parameterization:
            A = [[a, b], [b, c]]
            a-c = m^2-n^2,  b = mn,  sqrt(discriminant) = m^2+n^2
            eigenvalues = ((a+c) +/- (m^2+n^2)) / 2
        """
        for _ in range(200):
            m, n = MatrixGenerator._pythagorean_triple()
            diff = m * m - n * n
            b = m * n
            sqrt_disc = m * m + n * n

            sign = random.choice([-1, 1])
            diff_signed = sign * diff

            trace_min = eigen_min * 2
            trace_max = eigen_max * 2
            trace = random.randint(trace_min, trace_max)

            if (trace % 2) != (sqrt_disc % 2):
                if trace < trace_max:
                    trace += 1
                elif trace > trace_min:
                    trace -= 1
                else:
                    continue

            a = (trace + diff_signed) // 2
            c = (trace - diff_signed) // 2

            eig1 = (trace + sqrt_disc) // 2
            eig2 = (trace - sqrt_disc) // 2

            if (eigen_min <= eig1 <= eigen_max and eigen_min <= eig2 <= eigen_max
                    and eig1 != eig2):
                return [[a, b], [b, c]], [eig1, eig2]
        raise RuntimeError("Failed to generate 2x2 block after 200 attempts")

    @staticmethod
    def _random_permutation(size):
        """Return a random permutation of [0, 1, ..., size-1]."""
        perm = list(range(size))
        random.shuffle(perm)
        return perm

    @staticmethod
    def _apply_permutation_similarity(A, perm):
        """Apply permutation similarity transform: P*A*P^T where P is the permutation matrix."""
        n = len(A)
        result = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                result[i][j] = A[perm[i]][perm[j]]
        return result

    @staticmethod
    def generate(size, eigen_min, eigen_max):
        """Generate a size x size symmetric matrix with integer entries and integer eigenvalues.

        Returns (matrix_2d_list, eigenvalues_list).
        """
        if size == 2:
            matrix, eigvals = MatrixGenerator._generate_2x2_block(eigen_min, eigen_max)
            return matrix, sorted(eigvals, reverse=True)

        elif size == 3:
            block, eig_2x2 = MatrixGenerator._generate_2x2_block(eigen_min, eigen_max)
            lam3 = random.randint(eigen_min, eigen_max)
            while lam3 in eig_2x2:
                lam3 = random.randint(eigen_min, eigen_max)

            A = [
                [block[0][0], block[0][1], 0],
                [block[1][0], block[1][1], 0],
                [0, 0, lam3],
            ]
            eigvals = eig_2x2 + [lam3]

            if random.random() < 0.7:
                perm = MatrixGenerator._random_permutation(3)
                A = MatrixGenerator._apply_permutation_similarity(A, perm)

            return A, sorted(eigvals, reverse=True)

        elif size == 4:
            block1, eig1 = MatrixGenerator._generate_2x2_block(eigen_min, eigen_max)
            block2, eig2 = MatrixGenerator._generate_2x2_block(eigen_min, eigen_max)

            A = [
                [block1[0][0], block1[0][1], 0, 0],
                [block1[1][0], block1[1][1], 0, 0],
                [0, 0, block2[0][0], block2[0][1]],
                [0, 0, block2[1][0], block2[1][1]],
            ]
            eigvals = eig1 + eig2

            if random.random() < 0.7:
                perm = MatrixGenerator._random_permutation(4)
                A = MatrixGenerator._apply_permutation_similarity(A, perm)

            return A, sorted(eigvals, reverse=True)

        else:
            raise ValueError(f"Unsupported matrix size: {size}")

    @staticmethod
    def make_verification_script(matrix, eigenvalues, size):
        """Generate a standalone SymPy verification script for a pre-computed matrix."""
        expected_unique = sorted(set(eigenvalues), reverse=True)

        lines = ["A = Matrix(["]
        for i, row in enumerate(matrix):
            row_str = ", ".join(str(v) for v in row)
            comma = "," if i < len(matrix) - 1 else ""
            lines.append(f"    [{row_str}]{comma}")
        lines.append("])")
        lines.append(f"expected_unique = {expected_unique}")
        lines.append("eig_dict = A.eigenvals()")
        lines.append("computed_unique = sorted([k for k in eig_dict.keys()], reverse=True)")
        lines.append("assert A == A.T, 'Matrix is not symmetric'")
        lines.append("n = A.rows")
        lines.append("total_mult = sum(eig_dict.values())")
        lines.append("assert total_mult == n, f'Total multiplicity {total_mult} != size {n}'")
        lines.append("assert computed_unique == expected_unique, f'Eigenvalue mismatch: {computed_unique} vs {expected_unique}'")
        for i in range(len(matrix)):
            for j in range(len(matrix)):
                lines.append(f"assert A[{i},{j}].is_Integer, 'Entry A[{i},{j}] not integer'")
        lines.append("for val in computed_unique:")
        lines.append("    assert val.is_Integer, f'Eigenvalue {val} is not an integer'")
        lines.append("result = {")
        lines.append("    'matrix': A,")
        lines.append("    'eigenvalues': eig_dict,")
        lines.append("    'unique_eigenvalues': computed_unique,")
        lines.append("    'is_symmetric': True,")
        lines.append("    'all_integer_entries': True,")
        lines.append("    'all_integer_eigenvalues': True,")
        lines.append("}")

        return "\n".join(lines)

    @staticmethod
    def matrix_to_latex(matrix):
        """Convert a 2D integer list to LaTeX bmatrix format."""
        rows = []
        for row in matrix:
            rows.append(" & ".join(str(v) for v in row))
        return "\\begin{bmatrix}" + " \\\\ ".join(rows) + "\\end{bmatrix}"

    @staticmethod
    def matrix_to_python(matrix):
        """Convert a 2D integer list to a Python list-of-lists string."""
        return str(matrix)
