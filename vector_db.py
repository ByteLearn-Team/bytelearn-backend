"""
Vector Database Configuration using PostgreSQL + pgvector
Handles document embeddings storage and retrieval for RAG on Aiven cloud
"""

import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
import uuid
import json

load_dotenv()

class VectorDB:
    def __init__(self):
        """Initialize PostgreSQL connection and embedding model"""
        # Get vector database connection details from environment
        self.db_host = os.getenv("VECTOR_DB_HOST")
        self.db_port = os.getenv("VECTOR_DB_PORT", "5432")
        self.db_user = os.getenv("VECTOR_DB_USER")
        self.db_password = os.getenv("VECTOR_DB_PASSWORD")
        self.db_name = os.getenv("VECTOR_DB_NAME", "defaultdb")
        
        # Initialize embedding model (384-dimensional embeddings)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dimension = 384
        
        # Initialize connection (may be None if not configured)
        self.conn = None
        
        # Try to connect if credentials are provided
        if all([self.db_host, self.db_user, self.db_password]):
            print(f"☁️  Connecting to Aiven PostgreSQL vector database: {self.db_host}")
            try:
                self._connect()
                # Ensure tables exist if connection succeeded
                self._ensure_tables()
            except Exception as e:
                print(f"⚠️  Could not connect to PostgreSQL: {e}")
                print("⚠️  Vector database will be unavailable - RAG features disabled")
                self.conn = None
        else:
            print("⚠️  No vector database configured - RAG features disabled")
            print("   Set VECTOR_DB_HOST, VECTOR_DB_USER, VECTOR_DB_PASSWORD in .env to enable")
    
    def _connect(self):
        """Establish database connection"""
        # Build connection string
        self.conn_string = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}?sslmode=require"
        
        self.conn = psycopg.connect(self.conn_string, autocommit=False)
        register_vector(self.conn)
        print("✅ Connected to vector database successfully")
    
    def _ensure_connection(self):
        """Ensure connection is alive, reconnect if needed"""
        try:
            if self.conn is None or self.conn.closed:
                self._connect()
            else:
                # Test connection
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
        except Exception:
            self._connect()
    
    def _ensure_tables(self):
        """Create tables if they don't exist"""
        self._ensure_connection()
        
        with self.conn.cursor() as cur:
            # Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create documents table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bytelearn_documents (
                    id UUID PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector(384) NOT NULL,
                    metadata JSONB,
                    chapter_id INTEGER,
                    chapter_name TEXT,
                    subject TEXT,
                    class_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for vector similarity search (using cosine distance)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS bytelearn_documents_embedding_idx 
                ON bytelearn_documents 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            
            # Create indexes for common filters
            cur.execute("CREATE INDEX IF NOT EXISTS idx_chapter_id ON bytelearn_documents(chapter_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_subject ON bytelearn_documents(subject)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_class_id ON bytelearn_documents(class_id)")
            
            # Create quizzes table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bytelearn_quizzes (
                    id UUID PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector(384) NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS bytelearn_quizzes_embedding_idx 
                ON bytelearn_quizzes 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            
            self.conn.commit()
            print("✅ Vector database tables initialized")
    
    def create_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        embedding = self.embedding_model.encode(text)
        return embedding.tolist()
    
    def add_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        doc_id: Optional[str] = None
    ) -> str:
        """
        Add a document to the vector database
        
        Args:
            content: The text content to embed
            metadata: Additional metadata (subject, class_id, topic, chapter_id, chapter_name, etc.)
            doc_id: Optional document ID, generated if not provided
        
        Returns:
            Document ID (as UUID string)
        """
        self._ensure_connection()
        
        # Generate or validate UUID
        if not doc_id:
            doc_id = str(uuid.uuid4())
        else:
            try:
                uuid.UUID(doc_id)
            except (ValueError, AttributeError):
                doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(doc_id)))
        
        embedding = self.create_embedding(content)
        
        # Extract common fields for indexing
        chapter_id = metadata.get('chapter_id')
        chapter_name = metadata.get('chapter_name')
        subject = metadata.get('subject')
        class_id = metadata.get('class_id')
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bytelearn_documents 
                (id, content, embedding, metadata, chapter_id, chapter_name, subject, class_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    chapter_id = EXCLUDED.chapter_id,
                    chapter_name = EXCLUDED.chapter_name,
                    subject = EXCLUDED.subject,
                    class_id = EXCLUDED.class_id
            """, (doc_id, content, embedding, json.dumps(metadata), chapter_id, chapter_name, subject, class_id))
            
            self.conn.commit()
        
        return doc_id
    
    def add_documents_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add multiple documents in batch
        
        Args:
            documents: List of dicts with 'content' and 'metadata' keys
        
        Returns:
            List of document IDs
        """
        self._ensure_connection()
        
        doc_ids = []
        values = []
        
        for doc in documents:
            doc_id = doc.get('id', str(uuid.uuid4()))
            doc_ids.append(doc_id)
            
            embedding = self.create_embedding(doc['content'])
            metadata = doc.get('metadata', {})
            
            values.append((
                doc_id,
                doc['content'],
                embedding,
                json.dumps(metadata),
                metadata.get('chapter_id'),
                metadata.get('chapter_name'),
                metadata.get('subject'),
                metadata.get('class_id')
            ))
        
        with self.conn.cursor() as cur:
            for value in values:
                cur.execute("""
                    INSERT INTO bytelearn_documents 
                    (id, content, embedding, metadata, chapter_id, chapter_name, subject, class_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        chapter_id = EXCLUDED.chapter_id,
                        chapter_name = EXCLUDED.chapter_name,
                        subject = EXCLUDED.subject,
                        class_id = EXCLUDED.class_id
                """, value)
            self.conn.commit()
        
        return doc_ids
    
    def search_similar(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using cosine similarity
        
        Args:
            query: Search query text
            limit: Maximum number of results
            filters: Optional filters (e.g., {"chapter_id": 18, "subject": "Biology"})
            score_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of matching documents with scores
        """
        # Return empty list if no database connection
        if self.conn is None:
            print("⚠️  No vector database connection - returning empty results")
            return []
        
        self._ensure_connection()
        
        query_embedding = self.create_embedding(query)
        
        # Build WHERE clause for filters
        where_clauses = []
        filter_params = []
        
        if filters:
            print(f"🔍 Building filters for search: {filters}")
            for key, value in filters.items():
                if value is None:
                    continue  # Skip None values
                if isinstance(value, (list, tuple)):
                    placeholders = ','.join(['%s'] * len(value))
                    where_clauses.append(f"{key} = ANY(ARRAY[{placeholders}])")
                    filter_params.extend(value)
                else:
                    where_clauses.append(f"{key} = %s")
                    filter_params.append(value)
            print(f"📋 Filter clauses: {where_clauses}")
            print(f"📋 Filter params: {filter_params}")
        
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        
        # Search using cosine distance (1 - cosine_similarity)
        # Lower distance = more similar
        # We convert to similarity score (1 - distance) for consistency
        sql = f"""
            SELECT 
                id,
                content,
                metadata,
                chapter_id,
                chapter_name,
                subject,
                class_id,
                1 - (embedding <=> %s::vector) as score
            FROM bytelearn_documents
            {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT {limit}
        """
        
        # Combine params: embedding for similarity, filters, embedding for ORDER BY
        params = [query_embedding] + filter_params + [query_embedding]
        
        print(f"🔎 Executing vector search query with {len(filter_params)} filter params")
        
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            results = cur.fetchall()
        
        print(f"📊 Vector search returned {len(results)} raw results")
        
        # Log actual scores for debugging
        if results:
            scores = [row['score'] for row in results]
            print(f"📈 Similarity scores: min={min(scores):.4f}, max={max(scores):.4f}, avg={sum(scores)/len(scores):.4f}")
        
        # Filter by score threshold and format results
        formatted_results = []
        for row in results:
            score = float(row['score'])
            print(f"   Score: {score:.4f} for chapter_id={row['chapter_id']}, subject={row['subject']}")
            if score >= score_threshold:
                formatted_results.append({
                    'id': str(row['id']),
                    'content': row['content'],
                    'metadata': row['metadata'] or {},
                    'score': score,
                    'chapter_id': row['chapter_id'],
                    'chapter_name': row['chapter_name'],
                    'subject': row['subject'],
                    'class_id': row['class_id']
                })
        
        print(f"✅ Returning {len(formatted_results)} results after score threshold filter (>= {score_threshold})")
        
        return formatted_results
    
    def get_all_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve all documents (for browsing/debugging)
        
        Args:
            limit: Maximum number of documents to return
        
        Returns:
            List of documents with metadata
        """
        self._ensure_connection()
        
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT id, content, metadata, chapter_id, chapter_name, subject, class_id, created_at
                FROM bytelearn_documents
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            results = cur.fetchall()
        
        return [dict(row) for row in results]
    
    def count_documents(self) -> int:
        """Get total number of documents"""
        self._ensure_connection()
        
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM bytelearn_documents")
            count = cur.fetchone()[0]
        
        return count
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by ID"""
        self._ensure_connection()
        
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM bytelearn_documents WHERE id = %s", (doc_id,))
            self.conn.commit()
            return cur.rowcount > 0
    
    def clear_collection(self):
        """Clear all documents (use with caution!)"""
        self._ensure_connection()
        
        with self.conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE bytelearn_documents")
            self.conn.commit()
            print("✅ All documents cleared")
    
    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            print("🔌 Vector database connection closed")


# Global instance
vector_db = VectorDB()
