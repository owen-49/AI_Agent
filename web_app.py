import streamlit as st
from main import HigherAlgebraProfessorAgent
import time

st.set_page_config(page_title="MathGen-Agent: 高等代数题目生成器", layout="wide")

st.title("🎓 MathGen-Agent 高等代数题目动态生成系统")
st.markdown("---")

with st.sidebar:
    st.header("生成设置")
    topic = st.selectbox(
        "选择知识点",
        ["矩阵的初等变换与秩", "特征值与特征向量", "实对称矩阵的对角化", "二次型及其标准形", "线性空间的基与维数"]
    )
    difficulty = st.slider("难度等级", 1, 5, 3)
    generate_btn = st.button("生成题目")

if generate_btn:
    agent = HigherAlgebraProfessorAgent()
    
    with st.spinner(f"正在进行逻辑推演并验证 (知识点: {topic})..."):
        start_time = time.time()
        data = agent.generate_verified_problem(topic, difficulty)
        end_time = time.time()
    
    if data:
        st.success(f"生成成功！耗时: {end_time - start_time:.2f}秒")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📝 题干 (LaTeX)")
            st.info(data['latex_statement'])
            # 实时渲染 LaTeX
            st.latex(data['latex_statement'].replace('$', ''))
            
        with col2:
            st.subheader("💡 标准解析")
            st.write(data['analytical_solution'])
            
        st.markdown("---")
        st.subheader("⚙️ 符号计算脚本 (SymPy)")
        st.code(data['sympy_script'], language="python")
    else:
        st.error("生成失败，请尝试调整难度或重试。")