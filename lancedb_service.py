#!/usr/bin/env python3
"""
LanceDB Service - Vector Database for Personality Embeddings

Provides fast similarity search for user matching and conversation analysis.
Uses LanceDB for scalable vector storage and retrieval.
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# LanceDB client
try:
    import lancedb
    import pyarrow as pa
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False
    print("⚠️  LanceDB not installed. Install with: pip install lancedb pyarrow")

# Database path (local storage)
DB_PATH = os.getenv('LANCEDB_PATH', './lancedb_data')

def get_db():
    """Get or create LanceDB database connection."""
    if not LANCEDB_AVAILABLE:
        return None
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(DB_PATH, exist_ok=True)
        db = lancedb.connect(DB_PATH)
        return db
    except Exception as e:
        print(f"   ❌ Error connecting to LanceDB: {e}")
        return None

def get_user_embeddings_table():
    """Get or create user_embeddings table."""
    db_conn = get_db()
    if not db_conn:
        return None
    
    try:
        # Check if table exists
        if 'user_embeddings' in db_conn.table_names():
            return db_conn.open_table('user_embeddings')
        else:
            # Create table with schema
            schema = pa.schema([
                pa.field('user_id', pa.string()),
                pa.field('vector', pa.list_(pa.float32(), 1536)),  # 1536-dimensional vector
                pa.field('name', pa.string()),
                pa.field('school', pa.string()),
                pa.field('age', pa.string()),
                pa.field('hobbies', pa.string()),
                pa.field('updated_at', pa.timestamp('ns'))
            ])
            
            # Create empty table
            return db_conn.create_table(
                'user_embeddings',
                schema=schema,
                mode='overwrite'
            )
    except Exception as e:
        print(f"   ❌ Error getting user_embeddings table: {e}")
        return None

def get_conversation_embeddings_table():
    """Get or create conversation_embeddings table for future RAG use."""
    db_conn = get_db()
    if not db_conn:
        return None
    
    try:
        # Check if table exists
        if 'conversation_embeddings' in db_conn.table_names():
            return db_conn.open_table('conversation_embeddings')
        else:
            # Create table with schema for conversation embeddings
            schema = pa.schema([
                pa.field('conversation_id', pa.string()),
                pa.field('message_id', pa.string()),
                pa.field('vector', pa.list_(pa.float32(), 1536)),
                pa.field('text', pa.string()),
                pa.field('user_id', pa.string()),
                pa.field('created_at', pa.timestamp('ns'))
            ])
            
            return db_conn.create_table(
                'conversation_embeddings',
                schema=schema,
                mode='overwrite'
            )
    except Exception as e:
        print(f"   ⚠️  Error getting conversation_embeddings table: {e}")
        return None

def store_embedding(user_id: str, vector: List[float], profile: Optional[Dict] = None) -> bool:
    """
    Store user embedding in LanceDB.
    """
    print(f"DEBUG: store_embedding called for {user_id}")
    try:
        table = get_user_embeddings_table()
        if table is None:
            print("DEBUG: get_user_embeddings_table() returned None")
            return False
        
        # Ensure vector is float32 and exactly 1536 dimensions
        vector_float32 = [float(x) for x in vector[:1536]]
        if len(vector_float32) < 1536:
            vector_float32.extend([0.0] * (1536 - len(vector_float32)))
        elif len(vector_float32) > 1536:
            vector_float32 = vector_float32[:1536]
        
        # Prepare data
        data = {
            'user_id': user_id,
            'vector': vector_float32,
            'name': profile.get('name', '') if profile else '',
            'school': profile.get('school', '') if profile else '',
            'age': str(profile.get('age', '')) if profile else '',  # Ensure string
            'hobbies': profile.get('hobbies', '') if profile else '',
            'updated_at': datetime.now()
        }
        
        # Check if user already exists
        try:
            # Get all data and filter in pandas to avoid search syntax issues
            existing = table.to_pandas()
            if not existing.empty and 'user_id' in existing.columns:
                existing_user = existing[existing['user_id'] == user_id]
                if not existing_user.empty:
                    print(f"DEBUG: deleting existing user {user_id}")
                    table.delete(f"user_id = '{user_id}'")
        except Exception as e:
            print(f"DEBUG: check existence failed: {e}")
            # Continue anyway, duplicates might happen but it's better than failing
        
        print("DEBUG: adding data")
        table.add([data])
        print(f"   ✅ Stored embedding in LanceDB for {user_id}")
        return True
        
    except Exception as e:
        print(f"   ❌ Error storing embedding in LanceDB: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_embedding(user_id: str) -> Optional[List[float]]:
    """
    Retrieve user's embedding vector from LanceDB.
    """
    table = get_user_embeddings_table()
    if not table:
        return None
    
    try:
        # Get all data and filter in pandas
        all_data = table.to_pandas()
        if all_data.empty or 'user_id' not in all_data.columns:
            return None
        
        user_row = all_data[all_data['user_id'] == user_id]
        if user_row.empty or 'vector' not in user_row.columns:
            return None
        
        vector = user_row.iloc[0]['vector']
        if isinstance(vector, list):
            return [float(x) for x in vector]
        return None
        
    except Exception as e:
        print(f"   ❌ Error retrieving embedding from LanceDB: {e}")
        return None

def search_similar_users(query_vector: List[float], exclude_user_id: Optional[str] = None, limit: int = 5) -> List[Dict]:
    """
    Search for similar users using vector similarity.
    """
    table = get_user_embeddings_table()
    if not table:
        return []
    
    try:
        # Ensure vector is float32 and exactly 1536 dimensions
        query_vector_float32 = [float(x) for x in query_vector[:1536]]
        if len(query_vector_float32) < 1536:
            query_vector_float32.extend([0.0] * (1536 - len(query_vector_float32)))
        elif len(query_vector_float32) > 1536:
            query_vector_float32 = query_vector_float32[:1536]
        
        # Build search query - get more results to filter
        search_query = table.search(query_vector_float32).limit(limit * 3)
        
        # Execute search
        results = search_query.to_pandas()
        
        # Filter out excluded user and format results
        matches = []
        for _, row in results.iterrows():
            if exclude_user_id and row.get('user_id') == exclude_user_id:
                continue
            
            # LanceDB returns distance, convert to similarity score
            distance = row.get('_distance', 1.0)
            similarity_score = max(0.0, min(1.0, 1.0 - distance))
            
            match = {
                'user_id': row.get('user_id'),
                'score': similarity_score,
                'name': row.get('name', ''),
                'school': row.get('school', ''),
                'age': row.get('age', ''),
                'hobbies': row.get('hobbies', '')
            }
            matches.append(match)
            
            if len(matches) >= limit:
                break
        
        return matches
        
    except Exception as e:
        print(f"   ❌ Error searching similar users in LanceDB: {e}")
        return []

def store_conversation_embedding(conversation_id: str, message_id: str, vector: List[float], 
                                 text: str, user_id: str) -> bool:
    """
    Store conversation embedding for future RAG use.
    """
    table = get_conversation_embeddings_table()
    if not table:
        return False
    
    try:
        # Ensure vector is float32 and exactly 1536 dimensions
        vector_float32 = [float(x) for x in vector[:1536]]
        if len(vector_float32) < 1536:
            vector_float32.extend([0.0] * (1536 - len(vector_float32)))
        elif len(vector_float32) > 1536:
            vector_float32 = vector_float32[:1536]
        
        data = {
            'conversation_id': conversation_id,
            'message_id': message_id,
            'vector': vector_float32,
            'text': text,
            'user_id': user_id,
            'created_at': datetime.now()
        }
        
        table.add([data])
        return True
        
    except Exception as e:
        print(f"   ⚠️  Error storing conversation embedding: {e}")
        return False

def search_conversation_embeddings(query_vector: List[float], conversation_id: Optional[str] = None, 
                                   limit: int = 10) -> List[Dict]:
    """
    Search conversation embeddings for RAG.
    """
    table = get_conversation_embeddings_table()
    if not table:
        return []
    
    try:
        query_vector_float32 = [float(x) for x in query_vector[:1536]]
        if len(query_vector_float32) < 1536:
            query_vector_float32.extend([0.0] * (1536 - len(query_vector_float32)))
        elif len(query_vector_float32) > 1536:
            query_vector_float32 = query_vector_float32[:1536]
        
        search_query = table.search(query_vector_float32).limit(limit)
        
        if conversation_id:
            search_query = search_query.where(f"conversation_id = '{conversation_id}'")
        
        results = search_query.to_pandas()
        
        snippets = []
        for _, row in results.iterrows():
            distance = row.get('_distance', 1.0)
            similarity_score = max(0.0, min(1.0, 1.0 - distance))
            
            snippet = {
                'conversation_id': row.get('conversation_id'),
                'message_id': row.get('message_id'),
                'text': row.get('text', ''),
                'user_id': row.get('user_id', ''),
                'score': similarity_score
            }
            snippets.append(snippet)
        
        return snippets
        
    except Exception as e:
        print(f"   ⚠️  Error searching conversation embeddings: {e}")
        return []
