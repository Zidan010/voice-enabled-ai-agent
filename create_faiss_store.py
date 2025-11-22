import json
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import torch
from tqdm import tqdm

class FAISSVectorStore:
    """Create FAISS indices for agentic RAG system"""
    
    def __init__(self, embedding_model_name="sentence-transformers/all-mpnet-base-v2"):
        """
        Initialize with embedding model
        
        Args:
            embedding_model_name: HuggingFace model name
        """
        print(f"\n{'='*80}")
        print("INITIALIZING FAISS VECTOR STORE CREATOR")
        print(f"{'='*80}")
        
        # Load embedding model
        print(f"\nLoading embedding model: {embedding_model_name}")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        self.model = SentenceTransformer(embedding_model_name, device=self.device)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"Embedding dimension: {self.embedding_dim}")
        
        # Agent mapping (document name → agent name)
        self.AGENT_MAPPING = {
            "Artificial_Intelligence": {
                "agent_id": "Artificial_Intelligence",
                "name": "AI & Machine Learning Expert",
                "description": "Expert in artificial intelligence, machine learning, deep learning, neural networks, computer vision, NLP, robotics, and AI applications across various domains including transportation, healthcare, education, and employment."
            },
            "Cybersecurity": {
                "agent_id": "Cybersecurity",
                "name": "Cybersecurity Specialist",
                "description": "Specializes in cybersecurity frameworks, NIST standards, risk management, security controls, data protection, cyber threats, and organizational security policies."
            },
            "Digital_Health": {
                "agent_id": "Digital_Health",
                "name": "Digital Health Expert",
                "description": "Focuses on digital health strategies, healthcare technology, telemedicine, health information systems, patient data management, and healthcare digitalization globally."
            },
            "Human_Development": {
                "agent_id": "Human_Development",
                "name": "Human Development Specialist",
                "description": "Expert in human development, poverty reduction, inequality, education, mental health, social welfare, employment, and sustainable development goals."
            },
            "Renewable_Energy_Jobs": {
                "agent_id": "Renewable_Energy_Jobs",
                "name": "Renewable Energy & Jobs Expert",
                "description": "Specializes in renewable energy technologies (solar, wind, hydropower), green jobs, energy employment, sustainability, and clean energy transitions."
            }
        }
    
    def load_chunks(self, chunks_file: str) -> Dict[str, List[Dict]]:
        """
        Load chunks and group by document/agent
        
        Args:
            chunks_file: Path to chunks.json
            
        Returns:
            Dictionary mapping agent_id to list of chunks
        """
        print(f"\n{'='*80}")
        print("LOADING CHUNKS")
        print(f"{'='*80}")
        
        with open(chunks_file, 'r', encoding='utf-8') as f:
            all_chunks = json.load(f)
        
        print(f"Total chunks loaded: {len(all_chunks)}")
        
        # Group chunks by agent
        agent_chunks = {agent_id: [] for agent_id in self.AGENT_MAPPING.keys()}
        
        for chunk in all_chunks:
            document = chunk['document']
            if document in agent_chunks:
                agent_chunks[document].append(chunk)
            else:
                print(f"⚠ Warning: Unknown document '{document}' - skipping")
        
        # Print distribution
        print("\nChunks per agent:")
        for agent_id, chunks in agent_chunks.items():
            print(f"  {agent_id}: {len(chunks)} chunks")
        
        return agent_chunks
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for texts
        
        Args:
            texts: List of text strings
            batch_size: Batch size for encoding
            
        Returns:
            Numpy array of embeddings
        """
        print(f"  Generating embeddings (batch_size={batch_size})...")
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        
        return embeddings
    
    def create_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Create FAISS index from embeddings
        
        Args:
            embeddings: Numpy array of embeddings
            
        Returns:
            FAISS index
        """
        # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
        index = faiss.IndexFlatIP(self.embedding_dim)
        
        # Add embeddings to index
        index.add(embeddings.astype('float32'))
        
        return index
    
    def create_agent_index(self, agent_id: str, chunks: List[Dict], output_dir: str):
        """
        Create FAISS index and metadata for a single agent
        
        Args:
            agent_id: Agent identifier
            chunks: List of chunks for this agent
            output_dir: Output directory path
        """
        print(f"\n{'='*80}")
        print(f"CREATING INDEX FOR: {agent_id}")
        print(f"{'='*80}")
        print(f"Chunks: {len(chunks)}")
        
        if not chunks:
            print("⚠ No chunks found - skipping")
            return
        
        # Extract texts for embedding
        texts = [chunk['content'] for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.generate_embeddings(texts)
        print(f"  Embeddings shape: {embeddings.shape}")
        
        # Create FAISS index
        index = self.create_faiss_index(embeddings)
        print(f"  FAISS index created with {index.ntotal} vectors")
        
        # Prepare metadata
        metadata = {
            "agent_id": agent_id,
            "agent_name": self.AGENT_MAPPING[agent_id]["name"],
            "agent_description": self.AGENT_MAPPING[agent_id]["description"],
            "source_document": f"{agent_id}.pdf",
            "embedding_model": self.model.get_sentence_embedding_dimension(),
            "embedding_dimension": self.embedding_dim,
            "total_vectors": len(chunks),
            "chunks": []
        }
        
        # Add chunk metadata
        for i, chunk in enumerate(chunks):
            chunk_meta = {
                "vector_id": i,
                "chunk_id": chunk['chunk_id'],
                "content": chunk['content'],
                "section_path": chunk.get('section_path', []),
                "metadata": chunk.get('metadata', {})
            }
            metadata["chunks"].append(chunk_meta)
        
        # Create agent directory
        agent_dir = Path(output_dir) / "agents" / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        index_path = agent_dir / "faiss.index"
        faiss.write_index(index, str(index_path))
        print(f"  ✓ Saved FAISS index: {index_path}")
        
        # Save metadata
        metadata_path = agent_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved metadata: {metadata_path}")
        
        return {
            "agent_id": agent_id,
            "index_path": str(index_path),
            "metadata_path": str(metadata_path),
            "num_vectors": len(chunks)
        }
    
    def create_agent_registry(self, output_dir: str):
        """
        Create agent registry file for LLM router
        
        Args:
            output_dir: Output directory path
        """
        print(f"\n{'='*80}")
        print("CREATING AGENT REGISTRY")
        print(f"{'='*80}")
        
        registry = {
            "agents": {},
            "config": {
                "embedding_model": "sentence-transformers/all-mpnet-base-v2",
                "embedding_dimension": self.embedding_dim,
                "top_k": 2,
                "total_agents": len(self.AGENT_MAPPING)
            }
        }
        
        for agent_id, info in self.AGENT_MAPPING.items():
            registry["agents"][agent_id] = {
                "agent_id": agent_id,
                "name": info["name"],
                "description": info["description"],
                "index_path": f"agents/{agent_id}/faiss.index",
                "metadata_path": f"agents/{agent_id}/metadata.json"
            }
        
        registry_path = Path(output_dir) / "agent_registry.json"
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Agent registry created: {registry_path}")
        print(f"✓ Total agents: {len(self.AGENT_MAPPING)}")
        
        return registry
    
    def create_all_indices(self, chunks_file: str, output_dir: str):
        """
        Create all FAISS indices for all agents
        
        Args:
            chunks_file: Path to chunks.json
            output_dir: Output directory for vector store
        """
        # Load chunks
        agent_chunks = self.load_chunks(chunks_file)
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create index for each agent
        results = []
        for agent_id, chunks in agent_chunks.items():
            if chunks:
                result = self.create_agent_index(agent_id, chunks, output_dir)
                if result:
                    results.append(result)
        
        # Create agent registry
        registry = self.create_agent_registry(output_dir)
        
        # Print summary
        self.print_summary(results, output_dir)
        
        return results, registry
    
    def print_summary(self, results: List[Dict], output_dir: str):
        """Print creation summary"""
        print(f"\n{'='*80}")
        print("FAISS VECTOR STORE CREATION COMPLETE")
        print(f"{'='*80}")
        
        print(f"\nOutput directory: {output_dir}/")
        print(f"\nStructure created:")
        print(f"  {output_dir}/")
        print(f"  ├── agent_registry.json")
        print(f"  └── agents/")
        
        total_vectors = 0
        for result in results:
            agent_id = result['agent_id']
            num_vectors = result['num_vectors']
            total_vectors += num_vectors
            print(f"      ├── {agent_id}/")
            print(f"      │   ├── faiss.index ({num_vectors} vectors)")
            print(f"      │   └── metadata.json")
        
        print(f"\n{'='*80}")
        print(f"Summary:")
        print(f"  Total agents: {len(results)}")
        print(f"  Total vectors: {total_vectors}")
        print(f"  Embedding model: sentence-transformers/all-mpnet-base-v2")
        print(f"  Embedding dimension: {self.embedding_dim}")
        print(f"  Top-K per agent: 2")
        print(f"{'='*80}")
        
        print(f"\n✓ Ready for retrieval!")
        print(f"✓ Use the vector store with your LLM router and retrieval system")


class AgentRetriever:
    """Retrieval system for agentic RAG"""
    
    def __init__(self, vector_store_dir: str):
        """
        Initialize retriever
        
        Args:
            vector_store_dir: Path to vector store directory
        """
        self.vector_store_dir = Path(vector_store_dir)
        
        # Load agent registry
        registry_path = self.vector_store_dir / "agent_registry.json"
        with open(registry_path, 'r', encoding='utf-8') as f:
            self.registry = json.load(f)
        
        # Load embedding model
        model_name = self.registry['config']['embedding_model']
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(model_name, device=self.device)
        
        self.top_k = self.registry['config']['top_k']
        
        print(f"✓ AgentRetriever initialized")
        print(f"  Agents: {len(self.registry['agents'])}")
        print(f"  Top-K: {self.top_k}")
    
    def get_agent_descriptions(self) -> Dict[str, str]:
        """Get agent descriptions for LLM router"""
        descriptions = {}
        for agent_id, info in self.registry['agents'].items():
            descriptions[agent_id] = {
                "name": info['name'],
                "description": info['description']
            }
        return descriptions
    
    def search_agent(self, agent_id: str, query: str, k: int = None) -> List[Dict]:
        """
        Search specific agent's index
        
        Args:
            agent_id: Agent identifier
            query: Query text
            k: Number of results (default: from config)
            
        Returns:
            List of retrieved chunks with scores
        """
        if k is None:
            k = self.top_k
        
        # Load agent's FAISS index
        agent_info = self.registry['agents'][agent_id]
        index_path = self.vector_store_dir / agent_info['index_path']
        metadata_path = self.vector_store_dir / agent_info['metadata_path']
        
        # Load index and metadata
        index = faiss.read_index(str(index_path))
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Generate query embedding
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Search
        scores, indices = index.search(query_embedding.astype('float32'), k)
        
        # Prepare results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(metadata['chunks']):
                chunk = metadata['chunks'][idx].copy()
                chunk['score'] = float(score)
                chunk['agent_id'] = agent_id
                chunk['agent_name'] = agent_info['name']
                results.append(chunk)
        
        return results
    
    def search_multiple_agents(self, agent_ids: List[str], query: str, k: int = None) -> Dict[str, List[Dict]]:
        """
        Search multiple agents
        
        Args:
            agent_ids: List of agent identifiers
            query: Query text
            k: Number of results per agent
            
        Returns:
            Dictionary mapping agent_id to results
        """
        all_results = {}
        for agent_id in agent_ids:
            results = self.search_agent(agent_id, query, k)
            all_results[agent_id] = results
        
        return all_results
    
    def format_context(self, results: Dict[str, List[Dict]]) -> str:
        """
        Format retrieved chunks as context for LLM
        
        Args:
            results: Dictionary of agent results
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for agent_id, chunks in results.items():
            agent_name = self.registry['agents'][agent_id]['name']
            context_parts.append(f"\n{'='*80}")
            context_parts.append(f"Source: {agent_name}")
            context_parts.append(f"{'='*80}\n")
            
            for i, chunk in enumerate(chunks, 1):
                section = " > ".join(chunk['section_path']) if chunk['section_path'] else "N/A"
                context_parts.append(f"\n[Chunk {i}]")
                context_parts.append(f"Section: {section}")
                context_parts.append(f"Relevance Score: {chunk['score']:.4f}")
                context_parts.append(f"\n{chunk['content']}\n")
        
        return "\n".join(context_parts)


def main():
    """Main execution"""
    
    # Configuration
    CHUNKS_FILE = "chunks/chunks.json"
    OUTPUT_DIR = "vector_store"
    
    print("\n" + "="*80)
    print("FAISS VECTOR STORE CREATION FOR AGENTIC RAG")
    print("="*80)
    
    # Create vector store
    creator = FAISSVectorStore(
        embedding_model_name="sentence-transformers/all-mpnet-base-v2"
    )
    
    results, registry = creator.create_all_indices(
        chunks_file=CHUNKS_FILE,
        output_dir=OUTPUT_DIR
    )
    
    print("\n" + "="*80)
    print("TESTING RETRIEVAL SYSTEM")
    print("="*80)
    
    # Test retrieval
    retriever = AgentRetriever(OUTPUT_DIR)
    
    # Example: Get agent descriptions for router
    print("\nAgent Descriptions (for LLM Router):")
    descriptions = retriever.get_agent_descriptions()
    for agent_id, info in descriptions.items():
        print(f"\n{agent_id}:")
        print(f"  {info['description']}")
    
    # Example search
    print("\n" + "="*80)
    print("EXAMPLE SEARCH")
    print("="*80)
    
    test_query = "How does AI impact healthcare?"
    print(f"\nQuery: {test_query}")
    print(f"\nSearching agents: Artificial_Intelligence, Digital_Health")
    
    results = retriever.search_multiple_agents(
        agent_ids=["Artificial_Intelligence", "Digital_Health"],
        query=test_query,
        k=2
    )
    
    print(f"\nResults retrieved:")
    for agent_id, chunks in results.items():
        print(f"  {agent_id}: {len(chunks)} chunks")
        for chunk in chunks:
            print(f"    - Score: {chunk['score']:.4f}, Section: {' > '.join(chunk['section_path'][:2])}")
    
    # Format as context
    context = retriever.format_context(results)
    print(f"\nFormatted context length: {len(context)} characters")
    
    print("\n" + "="*80)
    print("✓ SYSTEM READY FOR PRODUCTION USE")
    print("="*80)


if __name__ == "__main__":
    main()