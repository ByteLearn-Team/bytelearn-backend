"""
RAG Service for Doubt Clearing and Quiz Generation
Handles document retrieval and LLM integration
"""

from typing import List, Dict, Any, Optional
import os
from openai import OpenAI
from dotenv import load_dotenv
from vector_db import vector_db
import json
import traceback

load_dotenv()

class RAGService:
    def __init__(self):
        """Initialize RAG service with Groq (OpenAI-compatible API)"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
        self.model = os.getenv("OPENAI_MODEL", "llama-3.3-70b-versatile")
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)

    def get_relevant_context(
        self,
        query: str,
        subject: Optional[str] = None,
        class_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
        limit: int = 3
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Retrieve relevant context from vector database

        Returns:
            Tuple of (formatted_context_string, source_documents)
        """
        filters = {}
        if subject:
            filters["subject"] = subject
        if class_id:
            # Ensure class_id is an integer
            filters["class_id"] = int(class_id) if class_id else None
        if chapter_id:
            # Ensure chapter_id is an integer
            filters["chapter_id"] = int(chapter_id) if chapter_id else None

        try:
            # Log filters being used
            print(f"🔍 Searching vector DB with filters: {filters}")

            # Search for relevant documents - accept low scores as embeddings may not be perfect
            results = vector_db.search_similar(
                query=query,
                limit=limit,
                filters=filters if filters else None,
                score_threshold=-1.0  # Accept all results including negative scores
            )

            # Log results retrieved
            print(f"📚 Retrieved {len(results)} results from vector DB")

            if not results:
                print("⚠️ No results found in vector DB with current filters")
                # Try again without chapter_id filter if it exists
                if 'chapter_id' in filters:
                    print("🔄 Retrying without chapter_id filter...")
                    filters_without_chapter = {k: v for k, v in filters.items() if k != 'chapter_id'}
                    results = vector_db.search_similar(
                        query=query,
                        limit=limit,
                        filters=filters_without_chapter if filters_without_chapter else None,
                        score_threshold=-1.0  # Accept all results including negative scores
                    )
                    print(f"📚 Retrieved {len(results)} results without chapter filter")

            if not results:
                print("❌ Still no results found in vector DB")
                raise ValueError("No relevant documents found in vector DB.")
        except ValueError as ve:
            raise ve
        except Exception as e:
            print(f"❌ Error during vector DB search: {e}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"Failed to retrieve content from vector DB: {str(e)}")

        # Format context - truncate content to avoid token limits
        context_parts = []
        max_content_length = 3000  # Limit each document to ~750 tokens

        for i, result in enumerate(results, 1):
            content = result['content']
            # Truncate long content
            if len(content) > max_content_length:
                content = content[:max_content_length] + "\n... (content truncated)"

            context_parts.append(
                f"[Document {i}] (Relevance: {result['score']:.2f})\n"
                f"{content}\n"
            )

        context = "\n".join(context_parts) if context_parts else "No relevant documents found."

        return context, results

    async def clear_doubt(
        self,
        question: str,
        subject: Optional[str] = None,
        class_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
        student_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer student's doubt using RAG

        Args:
            question: Student's question
            subject: Subject filter
            class_id: Class filter
            chapter_id: Chapter filter
            student_context: Additional context about student's current topic

        Returns:
            Dict with answer, sources, and metadata
        """
        # Check if it's a casual greeting or small talk (not an educational question)
        casual_patterns = ['hi', 'hello', 'hey', 'hlo', 'hii', 'hola', 'good morning', 'good afternoon',
                          'good evening', 'how are you', 'whats up', 'sup', 'how r u', 'thanks', 'thank you',
                          'ok', 'okay', 'bye', 'goodbye', 'see you']

        question_lower = question.lower().strip()
        is_casual = any(pattern in question_lower for pattern in casual_patterns) and len(question.split()) <= 5

        # If it's casual conversation, respond without RAG
        if is_casual:
            casual_responses = {
                'hi': "Hello! I'm here to help you with your studies. What would you like to learn about today?",
                'hello': "Hello! How can I assist you with your learning today?",
                'hey': "Hey there! What topic would you like to explore?",
                'how are you': "I'm doing great, thanks for asking! Ready to help you learn. What's your question?",
                'thanks': "You're welcome! Feel free to ask if you have more questions.",
                'thank you': "You're welcome! I'm here whenever you need help.",
                'bye': "Goodbye! Happy learning!",
            }

            # Find matching response
            response = "Hello! I'm ByteLearn AI, your study assistant. Ask me any questions about your subjects!"
            for key, value in casual_responses.items():
                if key in question_lower:
                    response = value
                    break

            return {
                "success": True,
                "answer": response,
                "sources": [],
                "has_context": False,
                "model_used": self.model
            }

        # For actual educational questions, use RAG
        # Get relevant context from vector DB
        context, sources = self.get_relevant_context(
            query=question,
            subject=subject,
            class_id=class_id,
            chapter_id=chapter_id,
            limit=3
        )

        # Build the prompt
        system_prompt = """You are ByteLearn AI, an expert educational assistant.
Your role is to help students understand concepts clearly and accurately.

Guidelines:
- Answer based on the provided context documents
- Be clear, concise, and educational
- Use simple language appropriate for the student's level
- If the context doesn't contain enough information, acknowledge it
- Include examples when helpful
- Be encouraging and supportive"""

        user_prompt = f"""Context from course materials:
{context}

Student's Question: {question}

{f"Additional Context: {student_context}" if student_context else ""}

Please provide a clear, educational answer to help the student understand."""

        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )

            answer = response.choices[0].message.content

            return {
                "success": True,
                "answer": answer,
                "sources": [
                    {
                        "content": src["content"][:200] + "...",
                        "relevance_score": src["score"],
                        "metadata": src["metadata"]
                    }
                    for src in sources
                ],
                "has_context": len(sources) > 0,
                "model_used": self.model
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "answer": "I'm having trouble processing your question right now. Please try again.",
                "sources": []
            }

    async def generate_quiz(
        self,
        topic: str,
        subject: Optional[str] = None,
        class_id: Optional[int] = None,
        num_questions: int = 5,
        difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate quiz questions based on course content

        Args:
            topic: Topic for the quiz
            subject: Subject filter
            class_id: Class filter
            num_questions: Number of questions to generate
            difficulty: easy, medium, or hard

        Returns:
            Dict with quiz questions and metadata
        """
        # Get relevant context - use fewer documents for quiz to stay within token limits
        context, sources = self.get_relevant_context(
            query=topic,
            subject=subject,
            class_id=class_id,
            limit=2  # Reduced from 5 to avoid token limits
        )

        system_prompt = """You are ByteLearn Quiz Generator, an expert at creating educational assessments.

Your task is to generate high-quality multiple-choice questions based on the provided content.

Requirements for each question:
- Clear and unambiguous question text
- 4 options (A, B, C, D)
- Only one correct answer
- Educational and relevant to the content
- Appropriate difficulty level
- Brief explanation for the correct answer

Format your response as valid JSON array."""

        user_prompt = f"""Based on this course content:

{context}

Generate {num_questions} {difficulty} difficulty multiple-choice questions about: {topic}

Return ONLY a JSON array with this exact structure:
[
  {{
    "question": "Question text here?",
    "options": {{
      "A": "First option",
      "B": "Second option",
      "C": "Third option",
      "D": "Fourth option"
    }},
    "correct_answer": "A",
    "explanation": "Brief explanation why this is correct",
    "difficulty": "{difficulty}",
    "topic": "{topic}"
  }}
]"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=2000
            )

            # Parse the response
            content = response.choices[0].message.content

            # Extract JSON from response
            # Remove markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            questions = json.loads(content.strip())

            return {
                "success": True,
                "questions": questions,
                "topic": topic,
                "difficulty": difficulty,
                "total_questions": len(questions),
                "sources_used": len(sources),
                "has_context": len(sources) > 0
            }

        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to parse quiz questions: {str(e)}",
                "questions": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "questions": []
            }

    async def generate_adaptive_quiz(
        self,
        student_id: int,
        subject: str,
        weak_topics: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generate adaptive quiz based on student's weak areas

        Args:
            student_id: Student ID
            subject: Subject for the quiz
            weak_topics: List of topics student struggles with

        Returns:
            Personalized quiz
        """
        if not weak_topics:
            weak_topics = ["general"]

        # Combine weak topics for better context
        topic_query = " ".join(weak_topics)

        return await self.generate_quiz(
            topic=topic_query,
            subject=subject,
            num_questions=10,
            difficulty="medium"
        )


# Global instance
rag_service = RAGService()
