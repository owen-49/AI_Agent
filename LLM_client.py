import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 加载 .env 中的环境变量
load_dotenv()

def get_llm(model_name="gpt-4o", temperature=0.7):
    """
    初始化 LLM 客户端
    :param model_name: 使用的模型名称
    :param temperature: 随机性参数，0.7适合创意题目生成，0.2适合逻辑推理
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("请在 .env 文件中设置 OPENAI_API_KEY")
    
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key
    )

# 测试调用函数
def test_llm_connection():
    llm = get_llm()
    response = llm.invoke("请简要说明，为什么在解析几何中需要严格的参数对齐？")
    print(f"LLM 回复: {response.content}")

if __name__ == "__main__":
    test_llm_connection()