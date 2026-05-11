import streamlit as st
import sqlite3
import json
import datetime
import re
import time
from main import HigherAlgebraProfessorAgent

class OutputParser:
    LATEX_ENVS = r'matrix|pmatrix|bmatrix|Bmatrix|vmatrix|Vmatrix|array|aligned|gathered|cases|equation|align\*?'

    @classmethod
    def _wrap_latex_envs(cls, text):
        return re.sub(
            rf'(\\begin\{{(?P<env>{cls.LATEX_ENVS})\}}[\s\S]*?\\end\{{(?P=env)\}})',
            r'$$\1$$',
            text
        )

    @classmethod
    def clean_for_streamlit(cls, text):
        if not text:
            return ""

        text = text.replace('\\n', '\n')

        text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)

        text = re.sub(r'(?<!\\)\[([\s\S]*?\\begin\{[pBvV]matrix\}[\s\S]*?\\end\{[pBvV]matrix\}[\s\S]*?)\]', r'$$\1$$', text)

        text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text)

        parts = re.split(r'(\$\$[\s\S]*?\$\$)', text)
        result = []
        for part in parts:
            if part.startswith('$$') and part.endswith('$$'):
                result.append(part)
            else:
                sub_parts = re.split(r'(\$[^$\n]+?\$)', part)
                for sp in sub_parts:
                    if sp.startswith('$') and sp.endswith('$') and len(sp) > 2:
                        result.append(sp)
                    else:
                        result.append(cls._wrap_latex_envs(sp))
        return ''.join(result)


class ProblemDatabase:
    def __init__(self, db_name="math_bank.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS verified_problems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                difficulty INTEGER,
                problem_data TEXT,
                created_at DATETIME
            )
        ''')
        self.conn.commit()

    def save_problem(self, topic, difficulty, data):
        c = self.conn.cursor()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''
            INSERT INTO verified_problems (topic, difficulty, problem_data, created_at)
            VALUES (?, ?, ?, ?)
        ''', (topic, difficulty, json.dumps(data, ensure_ascii=False), timestamp))
        self.conn.commit()
        
    def get_recent_problems(self, limit=5):
        c = self.conn.cursor()
        c.execute('SELECT topic, difficulty, created_at FROM verified_problems ORDER BY id DESC LIMIT ?', (limit,))
        return c.fetchall()


st.set_page_config(
    page_title="MathGen-Agent | 神经符号命题系统", 
    page_icon="🎓", 
    layout="wide"
)

@st.cache_resource
def get_db():
    return ProblemDatabase()

db = get_db()

st.title("🎓 MathGen-Agent 神经符号动态命题系统")
st.markdown("基于 **DeepSeek-V4** 与 **SymPy** 形式化验证的高等代数自动化生成工作流。")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ 命题参数配置")
    topic = st.selectbox(
        "选择核心知识点",
        [
            "矩阵的初等变换与秩", 
            "实对称矩阵的对角化", 
            "二次型及其标准形", 
            "线性空间的基与维数",
            "线性变换的特征值与特征向量"
        ]
    )
    difficulty = st.slider("难度等级 (1=基础, 5=考研/竞赛)", 1, 5, 3)
    
    st.markdown("---")
    generate_btn = st.button("🚀 开始动态命题", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.subheader("📚 最近入库题目")
    recent_records = db.get_recent_problems()
    if recent_records:
        for record in recent_records:
            st.caption(f"▪️ {record[0]} (难度 {record[1]}) - {record[2][11:16]}")
    else:
        st.caption("暂无入库记录")

if generate_btn:
    agent = HigherAlgebraProfessorAgent()
    
    with st.spinner(f"正在进行神经符号推演与多步验证 (知识点: {topic})..."):
        start_time = time.time()
        data = agent.generate_verified_problem(topic, difficulty)
        end_time = time.time()
    
    if data:
        st.success(f"✅ 题目生成并通过物理沙箱验证！耗时: {end_time - start_time:.2f} 秒")
        
        db.save_problem(topic, difficulty, data)
        
        clean_statement = OutputParser.clean_for_streamlit(data.get('latex_statement', ''))
        clean_solution = OutputParser.clean_for_streamlit(data.get('analytical_solution', ''))
        
        tab1, tab2, tab3 = st.tabs(["📄 试题预览", "💡 详细解析", "🛠️ 符号逻辑审计"])
        
        with tab1:
            st.subheader(f"题目：{data.get('title', '高等代数综合题')}")
            with st.container(border=True):
                st.markdown(clean_statement)
                
        with tab2:
            st.subheader("标准参考解析")
            with st.container(border=True):
                st.markdown(clean_solution)
                
        with tab3:
            st.subheader("Agent 真值比对与代码审计")
            st.info(data.get('consistency_check', '系统已通过 SymPy 引擎对生成的数学对象进行了反向构造与真值校验。'))
            
            st.markdown("**底层物理沙箱验证脚本 (Python/SymPy)：**")
            st.code(data.get('sympy_script', '# 未提取到脚本'), language="python")
            
            st.markdown("**系统状态日志：**")
            st.json({
                "Status": "Verified ✅",
                "Reverse_Engineering_Protocol": "Active",
                "Hallucination_Detected": "False (Filtered)"
            })

        st.markdown("---")
        export_md = f"""# {data.get('title', '高等代数题')}
*生成时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}*
*难度等级: {'★' * difficulty}*

{clean_statement}

{clean_solution}
"""
        st.download_button(
            label="📥 一键导出为 Markdown (支持 LaTeX 渲染)",
            data=export_md,
            file_name=f"MathGen_{topic}_L{difficulty}.md",
            mime="text/markdown",
            type="secondary"
        )
        
    else:
        st.error("🚨 连续多次触发逻辑不一致警告，为保证学术严谨性，生成已自动终止。请尝试降低难度或重试。")