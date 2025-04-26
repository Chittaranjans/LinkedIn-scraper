
# import numpy as np
# from sentence_transformers import SentenceTransformer

# class EmbeddingGenerator:
#     def __init__(self, model_name="all-MiniLM-L6-v2"):
#         # Load a pre-trained model (you can choose a different model)
#         try:
#             self.model = SentenceTransformer(model_name)
#             self.model_loaded = True
#             print(f"Loaded embedding model: {model_name}")
#         except Exception as e:
#             print(f"Error loading embedding model: {str(e)}")
#             self.model_loaded = False
    
#     def generate_embedding(self, text, max_length=512):
#         """Generate embeddings for job text"""
#         if not self.model_loaded or not text:
#             return self._generate_random_embedding(max_length)
            
#         try:
#             # Generate embedding
#             embedding = self.model.encode(text)
            
#             # Convert to MongoDB format
#             mongodb_embedding = []
#             for value in embedding:
#                 mongodb_embedding.append({"$numberDouble": str(float(value))})
                
#             return mongodb_embedding
#         except Exception as e:
#             print(f"Error generating embedding: {str(e)}")
#             return self._generate_random_embedding(max_length)
    
#     def _generate_random_embedding(self, length=384):
#         """Generate a random embedding for testing purposes"""
#         import random
#         mongodb_embedding = []
#         for _ in range(length):
#             mongodb_embedding.append({"$numberDouble": str(random.uniform(-0.05, 0.05))})
#         return mongodb_embedding