import time
import json
from tqdm import tqdm
from main import HigherAlgebraProfessorAgent

def run_benchmark(topic, difficulty, num_trials=10):
    agent = HigherAlgebraProfessorAgent()
    results = {
        "total_trials": num_trials,
        "success_count": 0,
        "failed_count": 0,
        "total_time": 0,
        "problems": []
    }
    
    print(f"🔬 开始基准测试 | 知识点: {topic} | 样本量: {num_trials}")
    
    for i in tqdm(range(num_trials)):
        start_time = time.time()
        
        data = agent.generate_verified_problem(topic, difficulty)
        
        elapsed = time.time() - start_time
        results["total_time"] += elapsed
        
        if data:
            results["success_count"] += 1
            results["problems"].append({
                "trial": i + 1,
                "matrix_str": data.get("sympy_script", ""), 
                "time_taken": round(elapsed, 2)
            })
        else:
            results["failed_count"] += 1
            
    success_rate = (results["success_count"] / num_trials) * 100
    avg_time = results["total_time"] / num_trials if num_trials else 0
    
    print("\n" + "="*40)
    print("📊 评测报告 (Benchmark Report)")
    print("="*40)
    print(f"总体成功率 (Pass Rate): {success_rate:.1f}%")
    print(f"平均生成耗时: {avg_time:.2f} 秒/题")
    print("="*40)
    
    with open(f"benchmark_{topic}_diff{difficulty}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    run_benchmark("二次型及其标准形", 4, num_trials=5)