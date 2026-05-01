import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 1. 加载环境变量
load_dotenv()

def verify_llm_connection():
    print("--- 开始连接验证 ---")
    
    # 2. 检查环境变量是否存在
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("错误：未找到 OPENAI_API_KEY，请检查 .env 文件！")
        return

    try:
        # 3. 初始化客户端
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        
        # 4. 发送简单的测试请求
        print("正在连接模型...")
        response = llm.invoke("如果你收到这条消息，请回复：'系统连接成功，科研助手准备就绪。'")
        
        # 5. 输出结果
        print("\n[模型返回]:")
        print(response.content)
        print("\n--- 验证完成 ---")
        
    except Exception as e:
        print(f"\n连接过程中出现错误: {e}")
        print("建议检查：API Key 是否有效、网络连接（可能需要代理）或模型名称是否正确。")

if __name__ == "__main__":
    verify_llm_connection()