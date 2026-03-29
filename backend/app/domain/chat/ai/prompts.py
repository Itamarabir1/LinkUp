"""
Prompts לניתוח AI של שיחות צ'אט.
"""

SYSTEM_PROMPT = (
    "You are an expert ride-sharing coordinator for a community carpool group. "
    "You are professional, precise, and understand Hebrew slang."
)

# Define the expected JSON schema structure
JSON_SCHEMA = """
{
  "driver_name": "string (name of the driver)",
  "passenger_name": "string (name of the passenger)",
  "pickup_location": "string (where they will meet, use 'לא צוין' if not specified)",
  "meeting_time": "string (when they will meet, use 'לא צוין' if not specified)",
  "summary_hebrew": "string (brief summary in Hebrew)"
}
"""

# Example format showing how the JSON should look
JSON_EXAMPLE_FORMAT = """
{
  "driver_name": "name of the driver",
  "passenger_name": "name of the passenger",
  "pickup_location": "where they will meet",
  "meeting_time": "when they will meet",
  "summary_hebrew": "brief summary in Hebrew"
}
"""

FEW_SHOT_EXAMPLES = """
Example 1 - Confirmed ride:
Conversation:
יוסי: מישהו נוסע מחר מתל אביב לחיפה?
אורן: אני יוצא ב-08:00 בבוקר.
יוסי: מעולה, יכול לאסוף אותי מרכבת מרכז?
אורן: סגור, נתראה שם.

Expected JSON output:
{
  "driver_name": "אורן",
  "passenger_name": "יוסי",
  "pickup_location": "רכבת מרכז",
  "meeting_time": "08:00",
  "summary_hebrew": "אורן נוסע מחר ב-08:00 מתל אביב לחיפה ויאסוף את יוסי מרכבת מרכז. הטרמפ אושר."
}

Example 2 - Cancelled ride:
Conversation:
רוני: יוצאת מבאר שבע לאילת בשישי?
שיר: כן, אבל המכונית מלאה כבר, מצטערת...
רוני: אופס, אולי פעם אחרת.

Expected JSON output:
{
  "driver_name": "שיר",
  "passenger_name": "רוני",
  "pickup_location": "לא צוין",
  "meeting_time": "לא צוין",
  "summary_hebrew": "רוני ביקש להצטרף לטרמפ של שיר מבאר שבע לאילת בשישי, אבל הטרמפ בוטל כי המכונית מלאה."
}
"""

USER_PROMPT = f"""
You are given a conversation between a driver and a passenger.

Your task is to extract and summarize the ride-sharing details from the conversation.

Expected JSON schema:
{JSON_SCHEMA}

Generate the response in this JSON format:
{JSON_EXAMPLE_FORMAT}

If some information is missing or unclear, use "לא צוין" (not specified) for that field.
If the ride was not confirmed or cancelled, indicate that in the summary_hebrew field.

Return ONLY valid JSON.

{FEW_SHOT_EXAMPLES}
"""
