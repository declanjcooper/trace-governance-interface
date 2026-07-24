import streamlit as st
import zipfile
import lxml.etree as ET
from dataclasses import dataclass, field
from typing import List, Dict
import pandas as pd

@dataclass
class ChestnutNode:
    tag: str
    path: str
    text: str = ""
    style_id: str = "Normal" 
    children: List['ChestnutNode'] = field(default_factory=list)

class StructuralCompiler:
    def __init__(self, doc_path):
        self.archive = zipfile.ZipFile(doc_path)
        self.ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        self.styles = self._load_styles()
        self.schema_matrix = {
            "document/body/p/r/t": "Native_Narrative",
            "document/body/tbl/tr/tc/p/r/t": "Native_Tabular"
        }

    def _load_styles(self) -> Dict[str, str]:
        styles = {}
        try:
            with self.archive.open('word/styles.xml') as f:
                root = ET.parse(f).getroot()
                for style in root.findall('.//w:style', self.ns):
                    s_id = style.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}styleId')
                    name = style.find('.//w:name', self.ns)
                    styles[s_id] = name.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val') if name is not None else s_id
        except: pass
        return styles

    def build_dag(self, part_name: str) -> ChestnutNode:
        with self.archive.open(part_name) as f:
            root = ET.parse(f).getroot()
            return self._traverse_and_build(root, "root")

    def _traverse_and_build(self, element, current_path: str, current_style: str = "Normal") -> ChestnutNode:
        tag = element.tag.split('}')[-1]
        new_path = f"{current_path}/{tag}"
        
        if tag == 'p':
            pPr = element.find('w:pPr', self.ns)
            if pPr is not None:
                pStyle = pPr.find('w:pStyle', self.ns)
                if pStyle is not None:
                    current_style = pStyle.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')

        text_content = element.text.strip() if element.text and element.text.strip() else ""
        node = ChestnutNode(tag=tag, path=new_path, text=text_content, style_id=self.styles.get(current_style, current_style))

        for child in element:
            if isinstance(child.tag, str):
                node.children.append(self._traverse_and_build(child, new_path, current_style))
        return node

    def bifurcate(self, node: ChestnutNode, ledger: Dict):
        is_native = False
        for vector, state in self.schema_matrix.items():
            if node.path.endswith(vector):
                ledger["Validated"].append({"State": state, "Style": node.style_id, "Path": node.path, "Content": node.text})
                is_native = True
                break
        if not is_native and node.tag == 't' and node.text:
            ledger["Quarantined"].append({"Path": node.path, "Content": node.text})
        for child in node.children:
            self.bifurcate(child, ledger)

def main():
    st.set_page_config(layout="wide", page_title="Chestnut TRACE: Governance Pulse")
    st.title("Chestnut TRACE: Governance Pulse Engine")
    
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])
    
    if uploaded_file:
        compiler = StructuralCompiler(uploaded_file)
        root = compiler.build_dag('word/document.xml')
        ledger = {"Validated": [], "Quarantined": []}
        compiler.bifurcate(root, ledger)
        
        # Visualize the Pulse
        df_valid = pd.DataFrame(ledger["Validated"])
        if not df_valid.empty:
            st.subheader("Semantic Governance Pulse")
            # Convert Style names to numerical sequence for the pulse chart
            df_valid['Style_Idx'] = df_valid['Style'].astype('category').cat.codes
            st.line_chart(df_valid['Style_Idx'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(df_valid, use_container_width=True)
        with col2:
            st.data_editor(pd.DataFrame(ledger["Quarantined"]), use_container_width=True)

if __name__ == "__main__":
    main()
