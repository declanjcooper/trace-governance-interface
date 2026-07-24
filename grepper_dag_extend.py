import streamlit as st
import zipfile
import lxml.etree as ET
import pandas as pd
import json
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class ChestnutNode:
    tag: str
    path: str
    text: str = ""
    style_id: str = "Normal"
    children: List['ChestnutNode'] = field(default_factory=list)

class TemplateMatcher:
    """Defines the 'Ideal Pulse' of a compliant document."""
    EXPECTED_SEQUENCE = ["heading 1", "normal", "table header", "table bullet 0"]
    
    @staticmethod
    def analyze_compliance(ledger_data: List[Dict]) -> List[str]:
        violations = []
        # Basic pattern matching: check if styles exist in our expected template
        for i, item in enumerate(ledger_data):
            style = item['Style'].lower()
            if "heading" in style and i > 0 and "heading" in ledger_data[i-1]['Style'].lower():
                violations.append(f"Structural Anomaly at {item['Path']}: Consecutive Headers detected.")
        return violations

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
    root_container = {"Header": "Introduction/Pre-Header", "Style": "Heading 0", "Children": []}
    current_parent = root_container
    
    for item in ledger_data:
        if "heading" in item['Style'].lower():
            current_parent = {"Header": item['Content'], "Style": item['Style'], "Children": []}
            tree.append(current_parent)
        else:
            if current_parent == root_container and not tree:
                tree.insert(0, root_container)
            current_parent["Children"].append(item)
    return tree

def to_markdown(tree: List[Dict]) -> str:
    md = ""
    for section in tree:
        level = str(section['Style']).lower().replace('heading ', '')
        prefix = "#" * int(level) if level.isdigit() else "###"
        md += f"{prefix} {section['Header']}\n\n"
        for child in section['Children']:
            if child.get('State') == 'Native_Narrative':
                md += f"{child['Content']}\n\n"
            else:
                md += f"- {child['Content']}\n"
        md += "\n"
    return md

def main():
    st.set_page_config(layout="wide", page_title="Chestnut TRACE: Template Matcher")
    st.title("Chestnut TRACE: Structural Pattern Matching Engine")
    
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])
    
    if uploaded_file:
        compiler = StructuralCompiler(uploaded_file)
        root = compiler.build_dag('word/document.xml')
        ledger = {"Validated": [], "Quarantined": []}
        compiler.bifurcate(root, ledger)
        
        # Run Pattern Matching
        violations = TemplateMatcher.analyze_compliance(ledger["Validated"])
        
        tree = reconstruct_hierarchical_json(ledger["Validated"])
        md_output = to_markdown(tree)
        
        tab1, tab2, tab3 = st.tabs(["Governance Pulse & Compliance", "Reconstructed Markdown", "Export Artifacts"])
        
        with tab1:
            st.subheader("Structural Pattern Match Results")
            if violations:
                st.error(f"Pattern Mismatch Detected: {len(violations)} issues found.")
                for v in violations: st.warning(v)
            else:
                st.success("Document matches template signature.")
            
            st.line_chart(pd.DataFrame(ledger["Validated"])['Style'].astype('category').cat.codes)
            
        with tab2:
            st.markdown(md_output)
            
        with tab3:
            st.download_button("Download Tree JSON", json.dumps(tree, indent=4), "tree.json")
            st.download_button("Download Markdown Doc", md_output, "reconstruction.md")

if __name__ == "__main__":
    main()
