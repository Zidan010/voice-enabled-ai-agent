# import pdfplumber
# import re
# import os
# from collections import Counter


# def detect_header_footer(pdf):
#     headers = Counter()
#     footers = Counter()

#     for page in pdf.pages[:5]:  # detect using first 5 pages
#         text = page.extract_text()
#         if not text:
#             continue

#         lines = text.split("\n")
#         if len(lines) > 2:
#             headers[lines[0].strip()] += 1
#             footers[lines[-1].strip()] += 1

#     # Consider something header/footer if appears on 3+ pages
#     header = headers.most_common(1)[0][0] if headers and headers.most_common(1)[0][1] >= 3 else None
#     footer = footers.most_common(1)[0][0] if footers and footers.most_common(1)[0][1] >= 3 else None

#     return header, footer



# def clean_and_markdown_page(page, header, footer):
#     extracted = page.extract_words(extra_attrs=["size"])
#     if not extracted:
#         return ""

#     markdown = ""
#     prev_y = None
#     prev_size = None

#     blocks = []

#     # Group words by y-coordinate (line grouping)
#     for word in extracted:
#         line_y = round(word["top"], 1)
#         size = round(word["size"], 1)
#         txt = word["text"].strip()

#         if header and txt in header:
#             continue
#         if footer and txt in footer:
#             continue

#         blocks.append((line_y, size, txt))

#     # Group into lines
#     lines = {}
#     for y, size, txt in blocks:
#         if y not in lines:
#             lines[y] = {"size": size, "text": txt}
#         else:
#             lines[y]["text"] += " " + txt

#     # Sort by vertical position
#     sorted_lines = sorted(lines.items(), key=lambda x: x[0])

#     for y, info in sorted_lines:
#         size = info["size"]
#         text = info["text"].strip()

#         # Identify headings based on font size difference
#         if prev_size:
#             if size >= prev_size + 1.5:
#                 markdown += f"\n# {text}\n"
#             elif size >= prev_size + 1:
#                 markdown += f"\n## {text}\n"
#             elif size >= prev_size + 0.5:
#                 markdown += f"\n### {text}\n"
#             else:
#                 markdown += text + "\n"
#         else:
#             # First line on page — assume title or section
#             markdown += f"# {text}\n"

#         prev_size = size

#     return markdown



# def extract_pdf_to_markdown(pdf_path, output_path):
#     with pdfplumber.open(pdf_path) as pdf:
#         header, footer = detect_header_footer(pdf)

#         all_md = []

#         for page in pdf.pages:
#             page_md = clean_and_markdown_page(page, header, footer)
#             all_md.append(page_md)

#     combined = "\n".join(all_md)

#     # Final normalization: collapse multiple blank lines → one blank line
#     combined = re.sub(r"\n\s*\n+", "\n\n", combined).strip()

#     with open(output_path, "w", encoding="utf-8") as f:
#         f.write(combined)

#     print(f"Saved structured markdown → {output_path}")


# # -------- USE THIS --------
# input_folder = "extracted_pdfs"
# output_folder = "cleaned_texts"
# os.makedirs(output_folder, exist_ok=True)

# for pdf_name in os.listdir(input_folder):
#     if pdf_name.endswith(".pdf"):
#         pdf_path = os.path.join(input_folder, pdf_name)
#         output_path = os.path.join(output_folder, pdf_name.replace(".pdf", ".md"))
#         extract_pdf_to_markdown(pdf_path, output_path)



import re
import os
from pathlib import Path
import PyPDF2

class PDFCleaner:
    """Advanced PDF text cleaner with document-specific strategies"""
    
    def __init__(self, text, doc_name):
        self.text = text
        self.doc_name = doc_name
        self.doc_type = self.identify_doc_type(doc_name)
        self.cleaned_text = ""
        
    def identify_doc_type(self, filename):
        """Identify document type from filename"""
        filename_lower = filename.lower()
        
        if 'artificial' in filename_lower or 'ai' in filename_lower:
            return "Artificial_Intelligence"
        elif 'cyber' in filename_lower:
            return "Cybersecurity"
        elif 'digital' in filename_lower and 'health' in filename_lower:
            return "Digital_Health"
        elif 'human' in filename_lower or 'development' in filename_lower:
            return "Human_Development"
        elif 'renewable' in filename_lower or 'energy' in filename_lower:
            return "Renewable_Energy_Jobs"
        else:
            return "Generic"
        
    def clean(self):
        """Main cleaning pipeline"""
        print(f"\nCleaning: {self.doc_name}")
        print(f"Document Type: {self.doc_type}")
        
        # Apply document-specific cleaning
        if self.doc_type == "Artificial_Intelligence":
            self.cleaned_text = self.clean_ai_report()
        elif self.doc_type == "Cybersecurity":
            self.cleaned_text = self.clean_cybersecurity()
        elif self.doc_type == "Digital_Health":
            self.cleaned_text = self.clean_digital_health()
        elif self.doc_type == "Human_Development":
            self.cleaned_text = self.clean_human_dev()
        elif self.doc_type == "Renewable_Energy_Jobs":
            self.cleaned_text = self.clean_renewable_energy()
        else:
            self.cleaned_text = self.clean_generic()
        
        # Apply common cleaning steps
        self.cleaned_text = self.apply_common_cleaning(self.cleaned_text)
        
        # Format as markdown
        self.cleaned_text = self.format_as_markdown(self.cleaned_text)
        
        print(f"✓ Cleaned successfully ({len(self.cleaned_text):,} characters)")
        
        return self.cleaned_text
    
    def clean_ai_report(self):
        """Specific cleaning for AI Report"""
        text = self.text
        
        # Remove page numbers at top
        text = re.sub(r'^\d{1,3}\n', '', text, flags=re.MULTILINE)
        
        # Remove section headers that repeat
        text = re.sub(r'SECTION [IVX]+:.*?\n', '\n# ', text)
        
        # Clean footnote numbers in text
        text = re.sub(r'\s+\d+\s+', ' ', text)
        
        # Remove citation formatting but keep content
        text = re.sub(r'\s+\(.*?\d{4}\)\.?', '', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Clean figure references
        text = re.sub(r'Figure\s+\d+[:\.].*?\n', '', text)
        
        # Remove image-related text
        text = re.sub(r'Wikimedia Images.*?\n', '', text)
        text = re.sub(r'accessed.*?\d{4}.*?\n', '', text)
        
        return text
    
    def clean_cybersecurity(self):
        """Specific cleaning for Cybersecurity Framework"""
        text = self.text
        
        # Remove repeated headers
        text = re.sub(r'NIST CSWP 29.*?\d{4}\n', '', text)
        text = re.sub(r'The NIST Cybersecurity Framework.*?\n', '', text)
        text = re.sub(r'February \d+, \d{4}\n', '', text)
        
        # Clean bullet points - normalize
        text = re.sub(r'•\s+', '- ', text)
        
        # Remove figure references
        text = re.sub(r'Fig\.\s+\d+\..*?\n', '', text)
        text = re.sub(r'Figure\s+\d+.*?\n', '', text)
        
        # Remove appendix references inline
        text = re.sub(r'\(see Appendix [A-Z]\)', '', text)
        
        # Clean acronym repetitions
        text = re.sub(r'\s+\([A-Z]{2,}\)', '', text)
        
        return text
    
    def clean_digital_health(self):
        """Specific cleaning for Digital Health Strategy"""
        text = self.text
        
        # Remove page numbers
        text = re.sub(r'^\d{1,3}\n', '', text, flags=re.MULTILINE)
        
        # Remove photo credits and image references
        text = re.sub(r'Photo credit:.*?\n', '', text)
        text = re.sub(r'Getty Images.*?\n', '', text)
        
        # Clean strategic objective headers - convert to markdown
        text = re.sub(r'SO\d+\n', '\n## ', text)
        text = re.sub(r'Global strategy on digital health.*?STRATEGIC OBJECTIVES\n', '', text)
        text = re.sub(r'Global strategy on digital health.*?GUIDING PRINCIPLES\n', '', text)
        
        # Remove repetitive section markers
        text = re.sub(r'STRATEGIC OBJECTIVES\n', '\n# Strategic Objectives\n', text)
        text = re.sub(r'GUIDING PRINCIPLES\n', '\n# Guiding Principles\n', text)
        
        # Clean numbered lists - convert to markdown
        text = re.sub(r'^\d+\)\s+', '- ', text, flags=re.MULTILINE)
        
        return text
    
    def clean_human_dev(self):
        """Specific cleaning for Human Development Report"""
        text = self.text
        
        # Remove "OVERVIEW" repeated headers
        text = re.sub(r'OVERVIEW\d*\n', '', text)
        text = re.sub(r'HUMAN DEVELOPMENT REPORT.*?\n', '', text)
        
        # Clean quote artifacts
        text = re.sub(r'"\s+', ' ', text)
        text = re.sub(r'\s+"', ' ', text)
        
        # Remove figure captions and sources
        text = re.sub(r'Figure\s+\d+.*?\n', '', text)
        text = re.sub(r'Source:.*?\n', '', text)
        text = re.sub(r'Note:.*?\n', '', text)
        
        # Remove image references
        text = re.sub(r'©.*?istock.*?\n', '', text, flags=re.IGNORECASE)
        
        # Clean footnote numbers
        text = re.sub(r'(?<=\s)\d{1,3}(?=\s)', '', text)
        
        return text
    
    def clean_renewable_energy(self):
        """Specific cleaning for Renewable Energy Report"""
        text = self.text
        
        # Remove chapter headers - convert to markdown
        text = re.sub(r'CHAPTER\s+\d+', '\n# Chapter ', text)
        
        # Clean "EDITION th" artifacts
        text = re.sub(r'EDITION\s*th\n', '', text)
        
        # Remove figure numbers and captions
        text = re.sub(r'Figure\s+\d+.*?\n', '', text)
        
        # Clean box headers - convert to markdown callouts
        text = re.sub(r'Box\s+\d+', '\n> **Box**', text)
        
        # Remove source attributions
        text = re.sub(r'Source:.*?\n', '', text)
        
        # Clean statistical notations
        text = re.sub(r'Note:.*?\.', '', text)
        
        # Remove image credits extensively
        text = re.sub(r'©.*?(?:istock|shutterstock|stock).*?\n', '', text, flags=re.IGNORECASE)
        text = re.sub(r'©\s*[A-Za-z\s]+/\s*[a-z]+\n', '', text)
        
        # Clean measurement units spacing
        text = re.sub(r'(\d+)\s*(GW|MW|kW|%)', r'\1\2', text)
        
        # Remove RENEWABLE ENERGY repeated headers
        text = re.sub(r'RENEWABLE ENERGY.*?\n', '', text)
        text = re.sub(r'ANNUAL REVIEW \d{4}\n', '', text)
        
        return text
    
    def clean_generic(self):
        """Generic cleaning for unidentified documents"""
        text = self.text
        
        # Remove common image indicators
        text = re.sub(r'©.*?\n', '', text)
        text = re.sub(r'Photo.*?:.*?\n', '', text)
        text = re.sub(r'Image.*?:.*?\n', '', text)
        
        # Remove figure references
        text = re.sub(r'Figure\s+\d+.*?\n', '', text)
        text = re.sub(r'Table\s+\d+.*?\n', '', text)
        
        return text
    
    def apply_common_cleaning(self, text):
        """Common cleaning steps for all documents"""
        
        # Remove ALL image-related content patterns
        text = re.sub(r'©[^\n]*', '', text)  # Copyright symbols
        text = re.sub(r'[Pp]hoto\s+credit[^\n]*', '', text)
        text = re.sub(r'[Ii]mage\s+credit[^\n]*', '', text)
        text = re.sub(r'[Ii]mage\s+source[^\n]*', '', text)
        text = re.sub(r'Getty\s+Images[^\n]*', '', text)
        text = re.sub(r'Shutterstock[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'iStock[^\n]*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[Image[^\]]*\]', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove tabs
        text = text.replace('\t', ' ')
        
        # Clean up line breaks in middle of sentences
        text = re.sub(r'(?<=[a-z,])\n(?=[a-z])', ' ', text)
        
        # Remove special characters artifacts - convert to markdown
        text = re.sub(r'[•◦▪▫]', '-', text)
        text = re.sub(r'[■□●○]', '*', text)
        
        # Fix hyphenation at line breaks
        text = re.sub(r'-\s*\n\s*', '', text)
        
        # Remove standalone numbers (likely page numbers)
        text = re.sub(r'^\d{1,3}$', '', text, flags=re.MULTILINE)
        
        # Remove empty parentheses and brackets
        text = re.sub(r'\(\s*\)', '', text)
        text = re.sub(r'\[\s*\]', '', text)
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # Remove URLs
        text = re.sub(r'http[s]?://[^\s]+', '', text)
        text = re.sub(r'www\.[^\s]+', '', text)
        
        # Final whitespace cleanup
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and not line.isspace():
                # Skip lines that are just punctuation or numbers
                if not re.match(r'^[\d\s\-\*\.]+$', line):
                    lines.append(line)
        
        text = '\n'.join(lines)
        
        return text
    
    def format_as_markdown(self, text):
        """Format cleaned text as proper markdown"""
        
        # Add document title
        doc_title = self.doc_name.replace('_', ' ').replace('.pdf', '')
        markdown_text = f"# {doc_title}\n\n"
        
        # Add separator
        markdown_text += "---\n\n"
        
        # Add cleaned content
        markdown_text += text
        
        # Ensure proper spacing around headers
        markdown_text = re.sub(r'\n(#{1,6}\s)', r'\n\n\1', markdown_text)
        markdown_text = re.sub(r'(#{1,6}\s[^\n]+)\n', r'\1\n\n', markdown_text)
        
        # Clean up any remaining multiple blank lines
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
        
        return markdown_text


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""


def process_pdf_folder(input_folder, output_folder):
    """Process all PDFs in input folder and save cleaned text to output folder"""
    
    # Create output folder if it doesn't exist
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files from input folder
    input_path = Path(input_folder)
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {input_folder}")
        return
    
    print(f"\nFound {len(pdf_files)} PDF file(s) to process")
    print("="*80)
    
    # Process each PDF
    for pdf_file in pdf_files:
        print(f"\nProcessing: {pdf_file.name}")
        
        # Extract text from PDF
        raw_text = extract_text_from_pdf(pdf_file)
        
        if not raw_text:
            print(f"⚠ Skipping {pdf_file.name} - no text extracted")
            continue
        
        print(f"  Extracted {len(raw_text):,} characters")
        
        # Clean the text
        cleaner = PDFCleaner(raw_text, pdf_file.stem)
        cleaned_text = cleaner.clean()
        
        # Save cleaned text as markdown
        output_file = output_path / f"{pdf_file.stem}.md"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            print(f"  ✓ Saved to: {output_file.name}")
        except Exception as e:
            print(f"  ✗ Error saving {output_file.name}: {e}")
    
    print("\n" + "="*80)
    print("✓ All PDFs processed successfully!")
    print(f"✓ Cleaned files saved in: {output_folder}")
    print("="*80)


# Main Execution
def main():
    """Main execution function"""
    
    # Set your folder paths here
    INPUT_FOLDER = "extracted_pdfs"      # Folder containing your PDF files
    OUTPUT_FOLDER = "cleaned_texts"   # Folder where cleaned texts will be saved
    
    print("\n" + "="*80)
    print("PDF TEXT CLEANER FOR RAG PIPELINE")
    print("="*80)
    print(f"\nInput folder: {INPUT_FOLDER}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    
    # Process all PDFs
    process_pdf_folder(INPUT_FOLDER, OUTPUT_FOLDER)


if __name__ == "__main__":
    main()