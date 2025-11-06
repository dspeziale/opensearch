"""
DocSearch - Document Parser
Supporta: PDF, DOC, DOCX, Excel, HTML, Markdown, TXT
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
import logging

# PDF
import PyPDF2

# Word
from docx import Document

# Excel
import pandas as pd
import openpyxl

# HTML
from bs4 import BeautifulSoup

# Markdown
import markdown

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentParser:
    """Parser universale per documenti"""

    SUPPORTED_EXTENSIONS = {
        '.pdf': 'PDF Document',
        '.doc': 'Word Document',
        '.docx': 'Word Document',
        '.xls': 'Excel Spreadsheet',
        '.xlsx': 'Excel Spreadsheet',
        '.html': 'HTML Document',
        '.htm': 'HTML Document',
        '.md': 'Markdown Document',
        '.txt': 'Text Document',
        '.csv': 'CSV File'
    }

    def __init__(self):
        self.parsers = {
            '.pdf': self._parse_pdf,
            '.docx': self._parse_docx,
            '.doc': self._parse_docx,  # python-docx supporta anche .doc
            '.xlsx': self._parse_excel,
            '.xls': self._parse_excel,
            '.csv': self._parse_csv,
            '.html': self._parse_html,
            '.htm': self._parse_html,
            '.md': self._parse_markdown,
            '.txt': self._parse_text
        }

    def parse(self, file_path: str) -> Dict:
        """
        Parse un documento e ritorna metadati + contenuto

        Returns:
            {
                'filename': str,
                'extension': str,
                'type': str,
                'content': str,
                'metadata': dict,
                'success': bool,
                'error': str (optional)
            }
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return {
                'success': False,
                'error': f'File not found: {file_path}'
            }

        extension = file_path.suffix.lower()

        if extension not in self.parsers:
            return {
                'success': False,
                'error': f'Unsupported file type: {extension}'
            }

        try:
            # Parse del contenuto
            content = self.parsers[extension](file_path)

            # Metadata
            metadata = {
                'filename': file_path.name,
                'extension': extension,
                'type': self.SUPPORTED_EXTENSIONS.get(extension, 'Unknown'),
                'size': file_path.stat().st_size,
                'path': str(file_path.absolute())
            }

            # Estrai keywords e summary
            keywords = self._extract_keywords(content)
            summary = self._generate_summary(content)

            return {
                'success': True,
                'filename': file_path.name,
                'extension': extension,
                'type': metadata['type'],
                'content': content,
                'metadata': metadata,
                'keywords': keywords,
                'summary': summary
            }

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'filename': file_path.name
            }

    def _parse_pdf(self, file_path: Path) -> str:
        """Estrae testo da PDF"""
        text = []

        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)

            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text.append(f"\n--- Page {page_num + 1} ---\n")
                        text.append(page_text)
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num}: {e}")

        return '\n'.join(text)

    def _parse_docx(self, file_path: Path) -> str:
        """Estrae testo da Word DOCX"""
        doc = Document(file_path)

        text = []

        # Paragrafi
        for para in doc.paragraphs:
            if para.text.strip():
                text.append(para.text)

        # Tabelle
        for table in doc.tables:
            for row in table.rows:
                row_text = ' | '.join([cell.text for cell in row.cells])
                text.append(row_text)

        return '\n'.join(text)

    def _parse_excel(self, file_path: Path) -> str:
        """Estrae testo da Excel"""
        text = []

        # Leggi tutti i fogli
        excel_file = pd.ExcelFile(file_path)

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            text.append(f"\n=== Sheet: {sheet_name} ===\n")

            # Headers
            headers = ' | '.join(str(col) for col in df.columns)
            text.append(headers)
            text.append('-' * len(headers))

            # Rows (max 100 per performance)
            for idx, row in df.head(100).iterrows():
                row_text = ' | '.join(str(val) for val in row.values)
                text.append(row_text)

        return '\n'.join(text)

    def _parse_csv(self, file_path: Path) -> str:
        """Estrae testo da CSV"""
        df = pd.read_csv(file_path)

        text = []

        # Headers
        headers = ' | '.join(str(col) for col in df.columns)
        text.append(headers)
        text.append('-' * len(headers))

        # Rows (max 100)
        for idx, row in df.head(100).iterrows():
            row_text = ' | '.join(str(val) for val in row.values)
            text.append(row_text)

        return '\n'.join(text)

    def _parse_html(self, file_path: Path) -> str:
        """Estrae testo da HTML"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'lxml')

        # Rimuovi script e style
        for script in soup(["script", "style"]):
            script.decompose()

        # Estrai testo
        text = soup.get_text()

        # Pulizia
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text

    def _parse_markdown(self, file_path: Path) -> str:
        """Estrae testo da Markdown"""
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Converti a HTML poi a testo per avere output pulito
        html = markdown.markdown(md_content)
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()

        # Ma mantieni anche il markdown originale per contesto
        return f"=== MARKDOWN SOURCE ===\n{md_content}\n\n=== RENDERED TEXT ===\n{text}"

    def _parse_text(self, file_path: Path) -> str:
        """Estrae testo da file di testo"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def _extract_keywords(self, text: str, max_keywords: int = 20) -> List[str]:
        """
        Estrae keywords dal testo usando semplice analisi di frequenza
        """
        # Rimuovi punteggiatura e converti a lowercase
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())

        # Split in parole
        words = clean_text.split()

        # Rimuovi stopwords comuni (semplice)
        stopwords = {
            'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una',
            'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'e', 'è', 'che', 'del', 'della', 'dei', 'delle', 'nel', 'nella',
            'page', 'document', 'file', 'text'
        }

        # Filtra parole brevi e stopwords
        filtered_words = [
            word for word in words
            if len(word) > 3 and word not in stopwords
        ]

        # Conta frequenze
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Ordina per frequenza
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        # Prendi top N
        keywords = [word for word, freq in sorted_words[:max_keywords]]

        return keywords

    def _generate_summary(self, text: str, max_chars: int = 500) -> str:
        """
        Genera un breve summary del documento
        """
        # Prendi i primi N caratteri
        summary = text[:max_chars].strip()

        # Trova l'ultimo punto per non tagliare a metà frase
        last_period = summary.rfind('.')
        if last_period > 0:
            summary = summary[:last_period + 1]

        return summary


# Test
if __name__ == '__main__':
    parser = DocumentParser()

    # Test con un file markdown
    test_file = '../Documentazione/ai_soc_stack_guide.md'

    if os.path.exists(test_file):
        result = parser.parse(test_file)

        if result['success']:
            print(f"✅ Parsed: {result['filename']}")
            print(f"Type: {result['type']}")
            print(f"Content length: {len(result['content'])} chars")
            print(f"Keywords: {', '.join(result['keywords'][:10])}")
            print(f"\nSummary:\n{result['summary']}")
        else:
            print(f"❌ Error: {result['error']}")
    else:
        print(f"⚠️  Test file not found: {test_file}")
