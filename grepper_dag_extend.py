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
            "document/body/tbl/tr/tc/p/r/t": "Native_Tabular"
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

def reconstruct_hierarchical_json(ledger_data: List[Dict]) -> List[Dict]:
    tree = []
    root_container = {"Header": "Unstructured Content", "Style": "Normal", "Children": []}
    current_parent = root_container
    tree.append(current_parent)
    
    for item in ledger_data:
        is_heading = "heading" in item['Style'].lower() or \
                     (item['Content'].isupper() and 0 < len(item['Content']) < 60)
        
        if is_heading:
            current_parent = {"Header": item['Content'], "Style": item['Style'], "Children": []}
            tree.append(current_parent)
        else:
            current_parent["Children"].append(item)
    return tree

def get_semantic_rank(style_name: str) -> str:
    s = style_name.lower()
    if "heading" in s: return "Heading"
    if "table" in s: return "Table_Atom"
    if "normal" in s: return "Body_Text"
    return "Other"

def to_markdown(tree: List[Dict]) -> str:
    md = ""
    for section in tree:
        style_str = str(section['Style']).lower()
        level = style_str.replace('heading ', '')
        prefix = "#" * int(level) if level.isdigit() else "###"
        md += f"{prefix} {section['Header']}\n\n"
        for child in section['Children']:
            if child.get('State') == 'Native_Narrative':
                md += f"{child['Content']}\n\n"
            else:
                md += f"- {child['Content']}\n"
        md += "\n---\n\n"
    return md

def main():
    st.set_page_config(layout="wide", page_title="Chestnut TRACE: Finalized")
    st.title("Chestnut TRACE: Semantic Reconstruction Engine")
    
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])
    
    if uploaded_file:
        compiler = StructuralCompiler(uploaded_file)
        root = compiler.build_dag('word/document.xml')
        ledger = {"Validated": [], "Quarantined": []}
        compiler.bifurcate(root, ledger)
        
        tree = reconstruct_hierarchical_json(ledger["Validated"])
        md_output = to_markdown(tree)
        
        tab1, tab2, tab3 = st.tabs(["Governance Pulse", "Reconstructed Markdown", "Export Artifacts"])
        
        with tab1:
            st.subheader("Semantic Governance Pulse")
            if not ledger["Validated"]:
                st.warning("No validated semantic content found. Check Quarantine Ledger for anomalies.")
            else:
                df_valid = pd.DataFrame(ledger["Validated"])
                if 'Style' in df_valid.columns:
                    df_valid['Category'] = df_valid['Style'].apply(get_semantic_rank)
                    chart = alt.Chart(df_valid.reset_index()).mark_circle(size=80).encode(
                        x=alt.X('index', title='Atom Sequence'),
                        y=alt.Y('Category', sort=['Heading', 'Body_Text', 'Table_Atom', 'Other']),
                        color='Category',
                        tooltip=['index', 'Style', 'Content']
                    ).interactive()
                    st.altair_chart(chart, use_container_width=True)
            
        with tab2:
            st.subheader("Semantic Markdown Preview")
            st.markdown(md_output)
            
        with tab3:
            st.subheader("Download Artifacts")
            col_a, col_b = st.columns(2)
            with col_a:
                st.download_button("Download Hierarchical JSON", json.dumps(tree, indent=4), "tree.json")
            with col_b:
                st.download_button("Download Markdown Doc", md_output, "reconstruction.md")

if __name__ == "__main__":
    main()
