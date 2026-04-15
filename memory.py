import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime

class FridayMemory:

    def __init__(self):
        self.client = chromadb.PersistentClient(path="./friday_memory")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.collection = self.client.get_or_create_collection(
            name="friday_conversations"
        )

    def save_memory(self, conversation):
        timestamp = datetime.now().strftime("%Y-%m-%D %H:%M")

        text_to_store = f"[{timestamp}] {conversation}"

        embedding = self.model.encode(text_to_store).tolist()

        self.collection.add(
            documents=[text_to_store],
            embeddings=[embedding],
            ids=[timestamp + "_" + str(len(conversation))]
            
        )
    def get_relevant_memories(self, current_message, n_results=3):
        if self.collection.count() == 0:
            return ""
        embedding = self.model.encode(current_message).tolist()

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, self.collection.count())
        )

        if not results['documents'][0]:
            return ""

        memories = results['documents'][0]

        formatted = "Relevant memories from past conversions:\n"
        for memory in memories:
            formatted += f"- {memory}\n"

        return formatted

    def build_memory_prompt(self, current_message):
        memories = self.get_relevant_memories(current_message)

        if not memories:
            return ""

        return f"\n{memories}\nUse these memories naturally in conversations without explictiy saying 'according to my records' or anything robotic.\n"