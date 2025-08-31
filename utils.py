import google.generativeai as genai
import json

def get_ai_greeting(api_key, user_memories):
    """
    Generates a smart, personalized greeting.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    Based on the user memories, write a single, short, warm welcoming sentence for a journal dashboard.
    - If you know the user's name, you must use it in the greeting.
    - If the memories are the default "My name is..." or are empty, provide a generic and welcoming greeting for a new user.
    - You can get creative, but keep it under 15 words.

    Memories:
    ---
    {user_memories}
    ---

    Your Greeting:
    """
    try:
        response = model.generate_content(prompt)
        # Clean up potential markdown or quotes
        return response.text.strip().replace("*", "").replace("\"", "")
    except Exception:
        return "Welcome back! Ready to write?"

def get_ai_analysis(api_key, entry_content, user_memories, ai_memories, forgotten_memories):
    """
    Analyzes a journal entry to provide a response and extract new memories.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    forgotten_memories_str = "\n- ".join(forgotten_memories)

    prompt = f"""
    You are an AI journaling companion. Your task is to analyze a new journal entry based on the user's provided memories.

    Primary Goal: Persona Adaptation
    First, carefully read the user's memories and the tone of their journal entry. Adapt your response to be congruent with their worldview and style.

    Task 1: Generate a Supportive Response
    Write a warm, empathetic response to the journal entry. React to their day, offer support for challenges, and celebrate successes. Do not ask questions.
    Your response should be thoughtful and detailed, but only long if the entry was long.

    Task 2: Extract New Memories
    Identify significant, new, and concrete facts from the entry that are not already present in memories or the forgotten list. Formulate each new fact as a concise, declarative sentence.

    Context:

    --- USER's CORE MEMORIES (User-provided, treat as ground truth) ---
    {user_memories}
    --- AI's LEARNED MEMORIES (Things I have learned about the user) ---
    {ai_memories}
    --- PERMANENTLY FORGOTTEN MEMORIES (Do NOT re-learn these facts) ---
    - {forgotten_memories_str}
    --- TODAY'S JOURNAL ENTRY ---
    {entry_content}
    --- REQUIRED OUTPUT (JSON format only) ---
    Return a single JSON object with two keys: "response" (a string) and "new_memory_sentences" (a JSON array of strings).
    """
    try:
        response = model.generate_content(prompt)
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        analysis = json.loads(cleaned_text)
        return analysis
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error processing AI analysis: {e}")
        return {
            "response": "I had a little trouble reflecting on your entry, but I've saved it for you.",
            "new_memory_sentences": []
        }

def perform_ai_search(api_key, search_query, all_entries_text):
    """
    Uses AI to find dates of entries relevant to a natural language search query.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    You are a search assistant for a personal journal. Read the following collection of journal entries and the user's search query.
    Your task is to identify which entries are most relevant to the query.

    Search Query: "{search_query}"

    Journal Entries:
    ---
    {all_entries_text}
    ---

    Instructions:
    1. Understand the user's intent. They might be asking about people, feelings, events, or specific topics.
    2. Find all entries that contain information relevant to the query.
    3. Return a single JSON object with one key: "relevant_dates".
    4. The value of "relevant_dates" must be a JSON array of strings, where each string is the date of a relevant entry in "YYYY-MM-DD" format.
    5. If no entries are relevant, return an empty array.
    """
    try:
        response = model.generate_content(prompt)
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        result = json.loads(cleaned_text)
        return result.get("relevant_dates", [])
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error processing AI search: {e}")
        return []