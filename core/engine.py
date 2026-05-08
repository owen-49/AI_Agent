import sys
from io import StringIO
import multiprocessing

class MathEngine:
    @staticmethod
    def verify_logic(script: str):
        
        buffer = StringIO()
        sys.stdout = buffer
        
        safe_globals = {
            "sympy": __import__("sympy"),
            "np": __import__("numpy"),
            "Matrix": __import__("sympy").Matrix,
            "symbols": __import__("sympy").symbols,
            "diag": __import__("sympy").diag,
        }
        
        try:
            local_env = {}
            exec(script, safe_globals, local_env)
            
            if "result" not in local_env:
                return False, "脚本运行成功但未定义变量 'result'"
            
            return True, local_env["result"]
        except Exception as e:
            return False, f"执行错误: {str(e)}"
        finally:
            sys.stdout = sys.__stdout__