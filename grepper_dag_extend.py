import streamlit as st
import zipfile
import lxml.etree as ET
import pandas as pd
import json
import altair as alt
from dataclasses import dataclass, field
from typing import List, Dict

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
            "document/body/tbl/tr/tc/p/r/t": "Native_Tabular",
            "txbxContent/p/r/t": "Native_Narrative"
        }

    def _load_styles(self):
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
        
        text = element.text.strip() if element.text and element.text.strip() else ""
        node = ChestnutNode(tag=tag, path=new_path, text=text, style_id=self.styles.get(current_style, current_style))
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

def get_semantic_rank(style_name: str) -> str:
    s = style_name.lower()
    if "heading" in s: return "Heading"
    if "table" in s: return "Table_Atom"
    if "normal" in s: return "Body_Text"
    return "Other"

def main():
    st.set_page_config(layout="wide", page_title="Chestnut TRACE")
    st.title("Chestnut TRACE: Comparative Governance Engine")
    
    mode = st.radio("Audit Mode", ["Single SOP Audit", "Template vs. Variant"])
    
    if mode == "Single SOP Audit":
        uploaded_files = st.file_uploader("Upload SOPs for Comparison", type=["docx"], accept_multiple_files=True)
        if uploaded_files:
            all_data = []
            for file in uploaded_files:
                compiler = StructuralCompiler(file)
                root = compiler.build_dag('word/document.xml')
                ledger = {"Validated": [], "Quarantined": []}
                compiler.bifurcate(root, ledger)
                df = pd.DataFrame(ledger["Validated"])
                df['Source'] = file.name
                df['Category'] = df['Style'].apply(get_semantic_rank)
                all_data.append(df)
            combined_df = pd.concat(all_data, ignore_index=True)
            
            selected_sources = st.multiselect("Select SOPs to Compare", combined_df['Source'].unique(), default=combined_df['Source'].unique())
            filtered_df = combined_df[combined_df['Source'].isin(selected_sources)]
            
            chart = alt.Chart(filtered_df.reset_index()).mark_circle(size=80).encode(
                x=alt.X('index', title='Atom Sequence'),
                y=alt.Y('Category', sort=['Heading', 'Body_Text', 'Table_Atom', 'Other']),
                color='Source', column='Source', tooltip=['Source', 'Category', 'Style', 'Content']
            ).properties(width=300).interactive()
            st.altair_chart(chart, use_container_width=True)

    elif mode == "Template vs. Variant":
        col1, col2 = st.columns(2)
        ref_file = col1.file_uploader("Upload Master Template (Reference)", type=["docx"])
        var_files = col2.file_uploader("Upload SOPs to Audit (Variants)", type=["docx"], accept_multiple_files=True)
        
        if ref_file and var_files:
            all_data = []
            # Reference
            ref_compiler = StructuralCompiler(ref_file)
            root = ref_compiler.build_dag('word/document.xml')
            ledger = {"Validated": [], "Quarantined": []}
            ref_compiler.bifurcate(root, ledger)
            df_ref = pd.DataFrame(ledger["Validated"])
            df_ref['Source'] = f"REF: {ref_file.name}"
            df_ref['Category'] = df_ref['Style'].apply(get_semantic_rank)
            all_data.append(df_ref)
            
            # Variants
            for file in var_files:
                compiler = StructuralCompiler(file)
                root = compiler.build_dag('word/document.xml')
                ledger = {"Validated": [], "Quarantined": []}
                compiler.bifurcate(root, ledger)
                df = pd.DataFrame(ledger["Validated"])
                df['Source'] = f"VAR: {file.name}"
                df['Category'] = df['Style'].apply(get_semantic_rank)
                all_data.append(df)
            
            combined_df = pd.concat(all_data, ignore_index=True)
            st.subheader("Comparative Structural Audit")
            chart = alt.Chart(combined_df.reset_index()).mark_circle(size=80).encode(
                x=alt.X('index', title='Atom Sequence'),
                y=alt.Y('Category', sort=['Heading', 'Body_Text', 'Table_Atom', 'Other']),
                color='Source', column='Source', tooltip=['Source', 'Category', 'Style', 'Content']
            ).properties(width=250).interactive()
            st.altair_chart(chart, use_container_width=True)

if __name__ == "__main__":
    main()
