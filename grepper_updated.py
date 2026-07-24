import streamlit as st
import zipfile
import lxml.etree as ET

class ChestnutPackageAuditor:
    """
    A structural auditor that treats the XML hierarchy as the SSOT.
    Recursively descends the tree to map every atom in the package.
    """
    def __init__(self, file_path):
        self.archive = zipfile.ZipFile(file_path)

    def get_xml_root(self, file_path):
        """Opens a specific XML part and returns the root element."""
        with self.archive.open(file_path) as f:
            return ET.parse(f).getroot()

    def recursive_traverse(self, node, depth=0):
        """
        Top-down traversal of the XML schema.
        Includes defensive checks to skip non-element XML nodes (e.g., comments).
        """
        # Ensure the node is a standard Element; skip comments/instructions
        if not isinstance(node.tag, str):
            return

        # Clean tag name (remove namespace)
        tag = node.tag.split('}')[-1]
        
        # Display the node with depth-based indentation for visual hierarchy
        content = node.text.strip() if node.text and node.text.strip() else ""
        st.text(f"{'  ' * depth}└─ {tag} {f'| Content: {content}' if content else ''}")
        
        # Recursively descend into children
        for child in node:
            self.recursive_traverse(child, depth + 1)

def main():
    st.set_page_config(layout="wide", page_title="Chestnut Auditor")
    st.title("Chestnut Package-Level Auditor")
    
    uploaded_file = st.file_uploader("Upload .docx", type=["docx"])

    if uploaded_file:
        try:
            auditor = ChestnutPackageAuditor(uploaded_file)
            # Starting the audit at the core content layer
            root = auditor.get_xml_root('word/document.xml')
            
            st.subheader("Structural Hierarchy (SSOT)")
            auditor.recursive_traverse(root)
            
        except Exception as e:
            st.error(f"Audit failed: {e}")

if __name__ == "__main__":
    main()
