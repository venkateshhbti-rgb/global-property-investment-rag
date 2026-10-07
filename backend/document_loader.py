import os
import json
from pathlib import Path
from typing import List, Dict, Any
import PyPDF2
import pandas as pd
from langchain.schema import Document
from config import settings

class PropertyDocumentLoader:
    """Dynamically loads and processes property investment documents from configured directories."""

    def __init__(self):
        self.base_path = Path(settings.DATA_BASE_PATH)
        self.documents = []

    def load_all_documents(self) -> List[Document]:
        """Load every sub-folder of the data directory; the folder name is the market (city or country)."""
        self.documents = []

        if not self.base_path.exists():
            print(f"Data folder not found: {self.base_path.resolve()}")
            return self.documents

        for folder in sorted(p for p in self.base_path.iterdir() if p.is_dir() and not p.name.startswith(".")):
            print(f"Loading {folder.name} data from: {folder}")
            self.documents.extend(self._load_directory(folder, region=folder.name))

        print(f"Total documents loaded: {len(self.documents)}")
        return self.documents

    def _load_directory(self, directory: Path, region: str) -> List[Document]:
        """Recursively load all documents from a directory."""
        documents = []

        for file_path in directory.rglob("*"):
            if file_path.is_file():
                try:
                    if file_path.suffix.lower() == ".pdf":
                        documents.extend(self._load_pdf(file_path, region))
                    elif file_path.suffix.lower() in [".csv"]:
                        documents.extend(self._load_csv(file_path, region))
                    elif file_path.suffix.lower() in [".json"]:
                        documents.extend(self._load_json(file_path, region))
                    elif file_path.suffix.lower() in [".txt"]:
                        documents.extend(self._load_text(file_path, region))
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")

        return documents

    def _load_pdf(self, file_path: Path, region: str) -> List[Document]:
        """Load and parse PDF documents."""
        documents = []
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        metadata = {
                            "source": str(file_path),
                            "file_name": file_path.name,
                            "region": region,
                            "document_type": "PDF",
                            "page_number": page_num + 1,
                        }
                        documents.append(Document(page_content=text, metadata=metadata))
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")

        return documents

    def _load_csv(self, file_path: Path, region: str) -> List[Document]:
        """Load and parse CSV files as documents."""
        documents = []
        try:
            df = pd.read_csv(file_path)
            # Group rows into chunks to create meaningful documents
            chunk_size = 10
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i+chunk_size]
                text = f"Data from {file_path.name} ({region}):\n"
                text += chunk.to_string(index=False)

                metadata = {
                    "source": str(file_path),
                    "file_name": file_path.name,
                    "region": region,
                    "document_type": "CSV",
                    "rows": len(chunk),
                    "columns": list(df.columns),
                }
                documents.append(Document(page_content=text, metadata=metadata))
        except Exception as e:
            print(f"Error reading CSV {file_path}: {e}")

        return documents

    def _load_json(self, file_path: Path, region: str) -> List[Document]:
        """Load and parse JSON files."""
        documents = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                text = json.dumps(data, indent=2)

                metadata = {
                    "source": str(file_path),
                    "file_name": file_path.name,
                    "region": region,
                    "document_type": "JSON",
                }
                documents.append(Document(page_content=text, metadata=metadata))
        except Exception as e:
            print(f"Error reading JSON {file_path}: {e}")

        return documents

    def _load_text(self, file_path: Path, region: str) -> List[Document]:
        """Load plain text files."""
        documents = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                if text.strip():
                    metadata = {
                        "source": str(file_path),
                        "file_name": file_path.name,
                        "region": region,
                        "document_type": "Text",
                    }
                    documents.append(Document(page_content=text, metadata=metadata))
        except Exception as e:
            print(f"Error reading text file {file_path}: {e}")

        return documents

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded documents."""
        stats = {
            "total_documents": len(self.documents),
            "by_region": {},
            "by_type": {},
            "total_characters": 0,
        }

        for doc in self.documents:
            region = doc.metadata.get("region", "Unknown")
            doc_type = doc.metadata.get("document_type", "Unknown")

            if region not in stats["by_region"]:
                stats["by_region"][region] = 0
            stats["by_region"][region] += 1

            if doc_type not in stats["by_type"]:
                stats["by_type"][doc_type] = 0
            stats["by_type"][doc_type] += 1

            stats["total_characters"] += len(doc.page_content)

        return stats
