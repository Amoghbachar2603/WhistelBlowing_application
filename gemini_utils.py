import os
from dotenv import load_dotenv
import google.generativeai as genai
import json

# Load environment variables
load_dotenv()

# Get API key from environment variable
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

# Configure the Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

def extract_fields(description):
    """
    Extract relevant fields from the incident description using Gemini.
    Returns a dictionary with extracted information.
    """
    try:
        # Initialize the model
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        # Create a prompt for field extraction
        prompt = f"""Analyze this incident description and extract specific information.
        Focus on identifying:
        1. Location: Where did the incident occur? (e.g., "library", "classroom 101", "main campus")
        2. Time: When did it happen? (e.g., "yesterday at 2 PM", "last week", "March 15, 2024")
        3. Category: What type of incident is this? Choose from:
           - Harassment (for unwanted behavior, comments, or advances)
           - Discrimination (for unfair treatment based on characteristics)
           - Bullying (for repeated aggressive behavior)
           - Academic Misconduct (for cheating, plagiarism, etc.)
           - Other (if none of the above fit)
        4. Accused: Who is the accused person or department? (e.g., "John Smith", "IT Department")

        Description: {description}

        Return ONLY a JSON object with these exact fields:
        {{
            "location": "extracted location or 'Not specified'",
            "time": "extracted time or 'Not specified'",
            "category": "one of: Harassment, Discrimination, Bullying, Academic Misconduct, or Other",
            "accused": "extracted accused or 'Not specified'"
        }}

        If any information is not clear or not mentioned, use "Not specified".
        For category, if unclear, use "Other".
        Be specific and accurate in the extraction."""

        # Generate response
        response = model.generate_content(prompt)
        
        # Get the response text and clean it
        response_text = response.text.strip()
        print("Raw Gemini response:", response_text)  # Debug print
        
        # Try to find and parse JSON in the response
        try:
            # First try direct JSON parsing
            result = json.loads(response_text)
        except json.JSONDecodeError:
            try:
                # Try to find JSON-like structure
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = response_text[start:end]
                    result = json.loads(json_str)
                else:
                    raise ValueError("No JSON object found in response")
            except Exception as e:
                print(f"Error parsing response: {str(e)}")
                print(f"Raw response: {response_text}")
                # Return default values
                return {
                    "location": "Not specified",
                    "time": "Not specified",
                    "category": "Other",
                    "accused": "Not specified"
                }

        # Validate and clean the extracted fields
        extracted_info = {
            "location": str(result.get("location", "Not specified")).strip(),
            "time": str(result.get("time", "Not specified")).strip(),
            "category": str(result.get("category", "Other")).strip(),
            "accused": str(result.get("accused", "Not specified")).strip()
        }

        # Validate category
        valid_categories = ["Harassment", "Discrimination", "Bullying", "Academic Misconduct", "Other"]
        if extracted_info["category"] not in valid_categories:
            extracted_info["category"] = "Other"

        # Clean up empty or None values
        for key in extracted_info:
            if not extracted_info[key] or extracted_info[key].lower() == "none":
                extracted_info[key] = "Not specified"

        print("Extracted information:", extracted_info)  # Debug print
        return extracted_info

    except Exception as e:
        print(f"Error in field extraction: {str(e)}")
        # Return default values in case of error
        return {
            "location": "Not specified",
            "time": "Not specified",
            "category": "Other",
            "accused": "Not specified"
        }

if __name__ == "__main__":
    incident_text = "Yesterday around 3 PM in the marketing department on the 5th floor, my supervisor John Smith made inappropriate comments."
    result = extract_fields(incident_text)
    print(result)