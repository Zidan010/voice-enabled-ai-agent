import re
import json
import csv
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
import tiktoken

@dataclass
class Chunk:
    """Represents a single text chunk with metadata"""
    chunk_id: str
    document: str
    section_path: List[str]
    content: str
    metadata: Dict
    
    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)


class MarkdownChunker:
    """Adaptive markdown chunker optimized for RAG pipeline"""
    
    def __init__(self, config=None):
        self.config = config or self.default_config()
        
        # Initialize tokenizer (using cl100k_base for GPT-3.5/4)
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except:
            print("⚠ tiktoken not available, using character estimation")
            self.tokenizer = None
    
    @staticmethod
    def default_config():
        """Default chunking configuration"""
        return {
            "target_chunk_size": 800,
            "min_chunk_size": 300,
            "max_chunk_size": 1200,
            "overlap_size": 100,
            "split_on": ["header_level_1", "header_level_2", "header_level_3", 
                        "paragraph", "sentence"],
            "keep_together": ["lists", "tables", "code_blocks", "blockquotes"],
            "include_section_path": True,
            "include_header_context": True,
            "include_prev_next_links": True,
            "estimate_tokens": True,
            "output_formats": ["json", "jsonl", "csv", "txt"],
            "create_stats": True
        }
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Fallback: estimate 1 token ≈ 4 characters
            return len(text) // 4
    
    def parse_markdown_structure(self, text: str) -> List[Dict]:
        """Parse markdown into structured sections"""
        sections = []
        lines = text.split('\n')
        
        current_section = {
            'level': 0,
            'header': 'Document Start',
            'content': [],
            'start_line': 0
        }
        
        header_stack = ['Document Start']
        
        for i, line in enumerate(lines):
            # Check for headers
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if header_match:
                # Save previous section
                if current_section['content']:
                    current_section['content'] = '\n'.join(current_section['content'])
                    sections.append(current_section)
                
                # Start new section
                level = len(header_match.group(1))
                header_text = header_match.group(2).strip()
                
                # Update header stack
                if level <= len(header_stack):
                    header_stack = header_stack[:level]
                header_stack.append(header_text)
                
                current_section = {
                    'level': level,
                    'header': header_text,
                    'header_stack': header_stack.copy(),
                    'content': [],
                    'start_line': i
                }
            else:
                # Add line to current section
                current_section['content'].append(line)
        
        # Save last section
        if current_section['content']:
            current_section['content'] = '\n'.join(current_section['content'])
            sections.append(current_section)
        
        return sections
    
    def split_long_section(self, text: str, max_tokens: int) -> List[str]:
        """Split a long section into smaller chunks by paragraphs/sentences"""
        chunks = []
        
        # Try splitting by paragraphs first
        paragraphs = text.split('\n\n')
        
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_tokens = self.count_tokens(para)
            
            # If single paragraph is too large, split by sentences
            if para_tokens > max_tokens:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                
                for sentence in sentences:
                    sent_tokens = self.count_tokens(sentence)
                    
                    if current_tokens + sent_tokens > max_tokens and current_chunk:
                        chunks.append('\n\n'.join(current_chunk))
                        # Keep overlap
                        overlap_text = current_chunk[-1] if current_chunk else ""
                        current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                        current_tokens = self.count_tokens('\n\n'.join(current_chunk))
                    else:
                        current_chunk.append(sentence)
                        current_tokens += sent_tokens
            
            # Normal paragraph
            elif current_tokens + para_tokens > max_tokens and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                # Keep overlap
                overlap_text = current_chunk[-1] if current_chunk else ""
                current_chunk = [overlap_text, para] if overlap_text else [para]
                current_tokens = self.count_tokens('\n\n'.join(current_chunk))
            else:
                current_chunk.append(para)
                current_tokens += para_tokens
        
        # Add remaining chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def create_chunks_from_sections(self, sections: List[Dict], doc_name: str) -> List[Chunk]:
        """Create chunks from parsed sections"""
        chunks = []
        chunk_index = 0
        
        current_chunk_sections = []
        current_tokens = 0
        current_header_stack = []
        
        for section in sections:
            section_text = section['content'].strip()
            if not section_text:
                continue
            
            section_header = section.get('header', '')
            section_tokens = self.count_tokens(section_text)
            header_stack = section.get('header_stack', [])
            
            # Update current header context
            if section_header:
                current_header_stack = header_stack
            
            # If section alone exceeds max size, split it
            if section_tokens > self.config['max_chunk_size']:
                # Save any accumulated chunks first
                if current_chunk_sections:
                    chunk = self.create_chunk(
                        current_chunk_sections,
                        doc_name,
                        chunk_index,
                        current_header_stack
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_chunk_sections = []
                    current_tokens = 0
                
                # Split the long section
                sub_chunks = self.split_long_section(section_text, self.config['max_chunk_size'])
                
                for sub_chunk_text in sub_chunks:
                    chunk = self.create_chunk(
                        [{'header': section_header, 'content': sub_chunk_text}],
                        doc_name,
                        chunk_index,
                        header_stack
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                continue
            
            # Check if adding this section would exceed target size
            if (current_tokens + section_tokens > self.config['target_chunk_size'] and 
                current_chunk_sections):
                
                # Create chunk from accumulated sections
                chunk = self.create_chunk(
                    current_chunk_sections,
                    doc_name,
                    chunk_index,
                    current_header_stack
                )
                chunks.append(chunk)
                chunk_index += 1
                
                # Start new chunk with overlap
                if current_chunk_sections:
                    overlap_text = current_chunk_sections[-1]['content']
                    overlap_tokens = self.count_tokens(overlap_text)
                    
                    if overlap_tokens <= self.config['overlap_size']:
                        current_chunk_sections = [current_chunk_sections[-1]]
                        current_tokens = overlap_tokens
                    else:
                        current_chunk_sections = []
                        current_tokens = 0
            
            # Add section to current chunk
            current_chunk_sections.append({
                'header': section_header,
                'content': section_text,
                'header_stack': header_stack
            })
            current_tokens += section_tokens
        
        # Create final chunk
        if current_chunk_sections:
            chunk = self.create_chunk(
                current_chunk_sections,
                doc_name,
                chunk_index,
                current_header_stack
            )
            chunks.append(chunk)
        
        # Add prev/next links
        for i, chunk in enumerate(chunks):
            chunk.metadata['total_chunks_in_doc'] = len(chunks)
            chunk.metadata['prev_chunk_id'] = chunks[i-1].chunk_id if i > 0 else None
            chunk.metadata['next_chunk_id'] = chunks[i+1].chunk_id if i < len(chunks)-1 else None
        
        return chunks
    
    def create_chunk(self, sections: List[Dict], doc_name: str, 
                    chunk_index: int, header_stack: List[str]) -> Chunk:
        """Create a single chunk from sections"""
        
        # Build content
        content_parts = []
        main_header = None
        
        for section in sections:
            if section['header'] and section['header'] != 'Document Start':
                if not main_header:
                    main_header = section['header']
                content_parts.append(f"## {section['header']}\n\n{section['content']}")
            else:
                content_parts.append(section['content'])
        
        content = '\n\n'.join(content_parts).strip()
        
        # Calculate metrics
        char_count = len(content)
        token_count = self.count_tokens(content)
        word_count = len(content.split())
        
        # Detect special content
        has_list = bool(re.search(r'^\s*[-*•]\s+', content, re.MULTILINE))
        has_numbered_list = bool(re.search(r'^\s*\d+\.\s+', content, re.MULTILINE))
        has_quote = bool(re.search(r'^\s*>\s+', content, re.MULTILINE))
        has_code = bool(re.search(r'```', content))
        
        # Build section path (breadcrumb)
        section_path = [h for h in header_stack if h != 'Document Start']
        
        # Create chunk ID
        chunk_id = f"{doc_name.lower().replace(' ', '_')}_chunk_{chunk_index:03d}"
        
        # Build metadata
        metadata = {
            'chunk_index': chunk_index,
            'char_count': char_count,
            'token_estimate': token_count,
            'word_count': word_count,
            'has_header': bool(main_header),
            'header_text': main_header,
            'header_level': len(header_stack),
            'parent_sections': section_path[:-1] if len(section_path) > 1 else [],
            'contains_list': has_list,
            'contains_numbered_list': has_numbered_list,
            'contains_quote': has_quote,
            'contains_code': has_code,
            'embedding_ready': True
        }
        
        return Chunk(
            chunk_id=chunk_id,
            document=doc_name,
            section_path=section_path,
            content=content,
            metadata=metadata
        )
    
    def chunk_document(self, file_path: str) -> List[Chunk]:
        """Chunk a single markdown document"""
        
        file_path = Path(file_path)
        doc_name = file_path.stem.replace('_cleaned', '')
        
        print(f"\nProcessing: {file_path.name}")
        
        # Read markdown file
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        print(f"  Characters: {len(text):,}")
        print(f"  Estimated tokens: {self.count_tokens(text):,}")
        
        # Parse structure
        sections = self.parse_markdown_structure(text)
        print(f"  Sections found: {len(sections)}")
        
        # Create chunks
        chunks = self.create_chunks_from_sections(sections, doc_name)
        print(f"  ✓ Created {len(chunks)} chunks")
        
        # Validate chunks
        self.validate_chunks(chunks, text)
        
        return chunks
    
    def validate_chunks(self, chunks: List[Chunk], original_text: str):
        """Validate chunk quality"""
        
        # Check size constraints
        undersized = []
        oversized = []
        
        for chunk in chunks:
            tokens = chunk.metadata['token_estimate']
            
            if tokens < self.config['min_chunk_size']:
                undersized.append((chunk.chunk_id, tokens))
            elif tokens > self.config['max_chunk_size']:
                oversized.append((chunk.chunk_id, tokens))
        
        if undersized:
            print(f"  ⚠ {len(undersized)} undersized chunks (< {self.config['min_chunk_size']} tokens)")
        
        if oversized:
            print(f"  ⚠ {len(oversized)} oversized chunks (> {self.config['max_chunk_size']} tokens)")
        
        # Check for empty chunks
        empty = [c.chunk_id for c in chunks if not c.content.strip()]
        if empty:
            print(f"  ⚠ {len(empty)} empty chunks found")
        
        # Calculate coverage (approximate)
        total_chunk_chars = sum(len(c.content) for c in chunks)
        coverage = (total_chunk_chars / len(original_text)) * 100
        print(f"  Coverage: {coverage:.1f}%")
    
    def save_chunks(self, all_chunks: Dict[str, List[Chunk]], output_dir: str):
        """Save chunks in multiple formats"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Flatten all chunks
        chunks_list = []
        for doc_chunks in all_chunks.values():
            chunks_list.extend(doc_chunks)
        
        print(f"\n{'='*80}")
        print(f"SAVING CHUNKS")
        print(f"{'='*80}")
        print(f"Total chunks: {len(chunks_list)}")
        
        # 1. Save as JSON
        if 'json' in self.config['output_formats']:
            json_path = output_path / 'chunks.json'
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump([c.to_dict() for c in chunks_list], f, indent=2, ensure_ascii=False)
            print(f"✓ Saved: {json_path.name}")
        
        # 2. Save as JSONL
        if 'jsonl' in self.config['output_formats']:
            jsonl_path = output_path / 'chunks.jsonl'
            with open(jsonl_path, 'w', encoding='utf-8') as f:
                for chunk in chunks_list:
                    f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + '\n')
            print(f"✓ Saved: {jsonl_path.name}")
        
        # 3. Save as CSV
        if 'csv' in self.config['output_formats']:
            csv_path = output_path / 'chunks.csv'
            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'chunk_id', 'document', 'section_path', 'content_preview',
                    'char_count', 'token_estimate', 'word_count', 'has_header'
                ])
                
                for chunk in chunks_list:
                    writer.writerow([
                        chunk.chunk_id,
                        chunk.document,
                        ' > '.join(chunk.section_path),
                        chunk.content[:100] + '...' if len(chunk.content) > 100 else chunk.content,
                        chunk.metadata['char_count'],
                        chunk.metadata['token_estimate'],
                        chunk.metadata['word_count'],
                        chunk.metadata['has_header']
                    ])
            print(f"✓ Saved: {csv_path.name}")
        
        # 4. Save individual text files
        if 'txt' in self.config['output_formats']:
            txt_dir = output_path / 'chunks_txt'
            txt_dir.mkdir(exist_ok=True)
            
            for chunk in chunks_list:
                txt_path = txt_dir / f"{chunk.chunk_id}.txt"
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(f"Document: {chunk.document}\n")
                    f.write(f"Section: {' > '.join(chunk.section_path)}\n")
                    f.write(f"Tokens: {chunk.metadata['token_estimate']}\n")
                    f.write(f"{'-'*80}\n\n")
                    f.write(chunk.content)
            
            print(f"✓ Saved: {len(chunks_list)} text files in {txt_dir.name}/")
        
        # 5. Save statistics
        if self.config['create_stats']:
            stats = self.generate_statistics(all_chunks)
            stats_path = output_path / 'chunking_statistics.json'
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2)
            print(f"✓ Saved: {stats_path.name}")
        
        print(f"\n✓ All chunks saved to: {output_dir}")
    
    def generate_statistics(self, all_chunks: Dict[str, List[Chunk]]) -> Dict:
        """Generate chunking statistics"""
        
        stats = {
            'total_documents': len(all_chunks),
            'total_chunks': sum(len(chunks) for chunks in all_chunks.values()),
            'documents': {}
        }
        
        all_tokens = []
        
        for doc_name, chunks in all_chunks.items():
            token_counts = [c.metadata['token_estimate'] for c in chunks]
            all_tokens.extend(token_counts)
            
            stats['documents'][doc_name] = {
                'chunk_count': len(chunks),
                'total_tokens': sum(token_counts),
                'avg_tokens': sum(token_counts) / len(token_counts) if token_counts else 0,
                'min_tokens': min(token_counts) if token_counts else 0,
                'max_tokens': max(token_counts) if token_counts else 0,
                'chunks_with_headers': sum(1 for c in chunks if c.metadata['has_header']),
                'chunks_with_lists': sum(1 for c in chunks if c.metadata['contains_list'])
            }
        
        # Overall stats
        stats['overall'] = {
            'total_tokens': sum(all_tokens),
            'avg_tokens_per_chunk': sum(all_tokens) / len(all_tokens) if all_tokens else 0,
            'min_tokens': min(all_tokens) if all_tokens else 0,
            'max_tokens': max(all_tokens) if all_tokens else 0,
            'target_chunk_size': self.config['target_chunk_size'],
            'overlap_size': self.config['overlap_size']
        }
        
        return stats


def main():
    """Main execution function"""
    
    # Configuration
    INPUT_DIR = "cleaned_texts"      # Folder with cleaned markdown files
    OUTPUT_DIR = "chunks"            # Folder for chunk outputs
    
    print("\n" + "="*80)
    print("ADAPTIVE MARKDOWN CHUNKER FOR RAG PIPELINE")
    print("="*80)
    print(f"\nInput directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Initialize chunker
    chunker = MarkdownChunker()
    
    print(f"\nChunking Configuration:")
    print(f"  Target chunk size: {chunker.config['target_chunk_size']} tokens")
    print(f"  Min chunk size: {chunker.config['min_chunk_size']} tokens")
    print(f"  Max chunk size: {chunker.config['max_chunk_size']} tokens")
    print(f"  Overlap: {chunker.config['overlap_size']} tokens")
    
    # Get all markdown files
    input_path = Path(INPUT_DIR)
    md_files = list(input_path.glob("*.md"))
    
    if not md_files:
        print(f"\n⚠ No markdown files found in {INPUT_DIR}")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(md_files)} markdown file(s) to chunk")
    print(f"{'='*80}")
    
    # Process each document
    all_chunks = {}
    
    for md_file in sorted(md_files):
        chunks = chunker.chunk_document(md_file)
        doc_name = md_file.stem.replace('_cleaned', '')
        all_chunks[doc_name] = chunks
    
    # Save all chunks
    print(f"\n{'='*80}")
    chunker.save_chunks(all_chunks, OUTPUT_DIR)
    
    # Print summary
    print(f"\n{'='*80}")
    print("CHUNKING SUMMARY")
    print(f"{'='*80}")
    
    for doc_name, chunks in all_chunks.items():
        tokens = [c.metadata['token_estimate'] for c in chunks]
        print(f"\n{doc_name}:")
        print(f"  Chunks: {len(chunks)}")
        print(f"  Avg tokens/chunk: {sum(tokens)/len(tokens):.0f}")
        print(f"  Range: {min(tokens)}-{max(tokens)} tokens")
    
    total_chunks = sum(len(chunks) for chunks in all_chunks.values())
    print(f"\n{'='*80}")
    print(f"✓ Total chunks created: {total_chunks}")
    print(f"✓ Ready for embedding and FAISS indexing!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()