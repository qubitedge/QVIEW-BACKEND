import io
import re
import fitz  # PyMuPDF
import docx

class ResumeParser:
    @staticmethod
    def parse_pdf(file_bytes: bytes) -> str:
        text = ""
        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                for page in doc:
                    text += page.get_text()
        except Exception as e:
            print(f"Error parsing PDF: {e}")
        return ResumeParser.clean_text(text)

    @staticmethod
    def parse_docx(file_bytes: bytes) -> str:
        text = ""
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            print(f"Error parsing DOCX: {e}")
        return ResumeParser.clean_text(text)

    @staticmethod
    def clean_text(text: str) -> str:
        # Remove extra whitespaces, newlines, and non-printable characters
        text = re.sub(r'\s+', ' ', text)
        text = ''.join(char for char in text if char.isprintable())
        return text.strip()

resume_parser = ResumeParser()
