import streamlit as st
import zipfile
import lxml.etree as ET

class ChestnutPackageAuditor:
    def __init__(self, file_path):
        self.archive = zipfile.ZipFile(file_path)
        self.ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    def get_xml_root(self, file_path):
        """Standardized way to get the root of any XML part in the container."""
        with self.archive.open(file_path) as f:
            return ET.parse(f).getroot()

    def recursive_traverse(self, node, depth=0):
        """Top-down recursive descent traversal of any XML part."""
        tag = node.tag.split('}')[-1]
        
        # Display the structural node
        st.write(f"{'  ' * depth} Node: {tag} | Text: {node.text.strip() if node.text else ''}")
        
        for child in node:
            self.recursive_traverse(child, depth + 1)

def main():
    st.title("Chestnut Package-Level Auditor")
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])

    if uploaded_file:
        auditor = ChestnutPackageAuditor(uploaded_file)
        # We target document.xml as the start, but we can now pivot 
        # to any part in the package (styles, settings, etc.)
        root = auditor.get_xml_root('word/document.xml')
        auditor.recursive_traverse(root)

if __name__ == "__main__":
    main()
