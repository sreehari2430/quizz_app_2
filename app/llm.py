import json
from google import genai
from .config import PROJECT_ID, LOCATION, MODEL_NAME, NUM_QUESTIONS_PER_QUIZ
from .models import Question
from .db import get_llm_input
from .logger import logger

def generate_questions(text):
    logger.info("start generate_questions")
    system_prompt = system_prompt = (
        "You are an expert teacher creating quiz questions **strictly from a given textbook chapter**.\n"
        "The goal is to test conceptual understanding based only on the provided syllabus-aligned text. "
        "You may use external facts only to support core concepts from the text.\n\n"
        
        "Instructions for question coverage:\n"
        "- For EVERY main concept keyword (category) derived from the textbook chapter, create one question for each difficulty level: 'easy', 'medium', 'hard'.\n"
        "- This means for every unique `category`, you will generate three questions: one easy, one medium, and one hard.\n"
        "- Combine each possible 'category' and 'difficulty_level' exactly once.\n\n"
        
        "For each question, follow this schema:\n"
        "- `answer`: The correct option (exact).\n"
        "- `prompt`: Clear, syllabus-aligned question.\n"
        "- `question_type`: Always 'multiple_choice'.\n"
        "- `hint`: Short hint related to the concept.\n"
        "- `explanation`: Why the correct option is right.\n"
        "- `choices`: Exactly 4 options (answer + 3 plausible distractors).\n"
        "- `difficulty_level`: One of: 'easy', 'medium', 'hard'.\n"
        "- `category`: The **main concept keyword only**, directly from the textbook content. "
        "Use only high-level scientific topics like 'acceleration', 'gravity', 'velocity', 'relative motion'. "
        "**Avoid vague or structural categories** like 'introduction', 'summary', 'example', 'definition', 'background'.\n\n"
        
        "Strictly follow the syllabus context. Use external knowledge only if it directly supports syllabus concepts. "
        "Return ONLY a JSON array of objects matching this schema—no extra text. "
        "Every combination of category and difficulty_level must be present once."
    )
    user_prompt = f"generate {NUM_QUESTIONS_PER_QUIZ} quiz questions using this content: {text}"
    client = genai.Client(vertexai=True, project="uday-452605", location="us-central1")
    response = client.models.generate_content(
                                          model=MODEL_NAME,
                                          contents=[system_prompt, user_prompt],
                                          config={
                                          "response_mime_type":"application/json",
                                          "response_schema":list[Question],}
                                          )
    try:
        questions = response.candidates[0].content.parts[0].text
        questions = json.loads(questions)
        logger.info("end generate_questions")        
        return questions
    except:
        return []
  
def get_llm_weights(user_id):
    input_data = get_llm_input(user_id)
    
    if not input_data["stats"]:
        print("No data available for LLM weights calculation.")
        return {}
    
    prompt = f"""
        You are an expert AI study coach.

        The user has completed quizzes in various categories. Your job is to:

        1. Analyze their performance (correct/total per category) and the last study plan.
        2. Generate category weights based on performance:
           - Higher weights for weaker categories (lower accuracy = higher weight).
           - Slightly increase weights for categories mentioned in the last_study_plan.
           - Use a scale of 0.1 to 1.0 per category.
           - Ensure all weights sum exactly to 1.0 (normalize them).
        3. Return ONLY a clean JSON object with category names as keys and weights as values.

        User's data:
        ```
        {json.dumps(input_data, indent=2)}
        ```

        Output exactly like:
        ```
        {{
            "category1": 0.25,
            "category2": 0.15
        }}
        ```
        """

    try:
      #   Replace with your actual LLM client call
        client = genai.Client(vertexai=True, project="uday-452605", location="us-central1")
        response = client.models.generate_content(
            model=MODEL_NAME, contents=[prompt], 
            config={"response_mime_type": "application/json"}
        )
        print("llm response from llm.py", response)
        return json.loads(response.text)
        
    except json.JSONDecodeError as e:
        print("Error decoding JSON from LLM response:", e)
        return {}
    except Exception as e:
        print("Error in LLM weights generation:", e)
        return {}
  
def generate_study_plan(category_stats, difficulty_stats, score_percent, total_questions):
    category_summary = ", ".join([f"{cat}: {stats['correct']} correct out of {stats['correct'] + stats['incorrect']}" for cat, stats in category_stats.items()])
    difficulty_summary = ", ".join([f"{diff}: {stats['correct']} correct out of {stats['correct'] + stats['incorrect']}" for diff, stats in difficulty_stats.items()])
    
    prompt = f"""
    You are an expert tutor creating a personalized study plan based on quiz results.
    Overall score: {score_percent:.1f}% ({int(score_percent / 100 * total_questions)} correct out of {total_questions}).
    Performance by category: {category_summary or 'No category data'}.
    Performance by difficulty: {difficulty_summary or 'No difficulty data'}.

    Generate a concise study plan as an HTML unordered list (<ul>) with 3-5 bullet points (<li> tags).
    Use HTML tags for formatting (e.g., <strong> for bold, no Markdown like **).
    Make it motivational, specific to weak areas, and suggest actionable steps.
    Return ONLY the <ul>...</ul> block—no extra text or wrappers.
    """

    try:
        client = genai.Client(vertexai=True, project="uday-452605", location="us-central1")
        response = response = client.models.generate_content(model=MODEL_NAME,
                                                             contents=[prompt])
        return response.text
    except Exception as e:
        print(f"Error generating study plan: {e}")
        return "<ul><li>Focus on weak areas and practice more.</li><li>Review explanations from your answers.</li></ul>"