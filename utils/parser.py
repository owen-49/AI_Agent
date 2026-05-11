import re

class OutputParser:
    @staticmethod
    def clean_for_streamlit(text):
        """
        清洗 LLM 输出的 LaTeX 文本，使其完美适配 Streamlit 的 Markdown 渲染
        """
        if not text:
            return ""
        
        # 将 literal 换行符替换为真正的换行
        text = text.replace('\\n', '\n')
        
        # 将 \[ ... \] 替换为 Streamlit 支持的 $$ ... $$
        text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
        
        # 将孤立的 [ ... ] 替换为 $$ ... $$ (针对你截图中的情况)
        text = re.sub(r'(?<!\\)\[([\s\S]*?\\begin\{pmatrix\}[\s\S]*?\\end\{pmatrix\}[\s\S]*?)\]', r'$$\1$$', text)
        
        return text