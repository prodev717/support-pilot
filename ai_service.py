import json
import urllib.parse
import requests
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, SERVER_URL, SIMILARITY_THRESHOLD

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_reply(prompt):
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text


def search_documents(query):
    if not query or not query.strip():
        return []
    encoded_query = urllib.parse.quote(query)
    url = f"{SERVER_URL}/search?query={encoded_query}"
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
        return [
            result["text"]
            for result in data.get("results", [])
            if result.get("score", 0.0) >= SIMILARITY_THRESHOLD
        ]
    except Exception as e:
        print(f"Search error: {e}")
        return []


def analyze_incoming_email(subject: str, email_body: str, department_rules: list[dict]) -> dict:
    """
    Analyse an incoming customer email and return a structured decision.

    Returns a dict with keys:
        issue, severity, sentiment, emotion,
        ai_decision, explanation, forward_to_email, draft_reply
    """
    # Pull relevant KB context
    docs = search_documents(email_body)
    context_block = "\n\n".join(docs[:5]) if docs else "No relevant knowledge base articles found."

    # Build department list for the model
    dept_lines = "\n".join(
        f"  - {r['department']}: {r['email']} — {r.get('description', '')}"
        for r in department_rules
    ) or "  (no departments configured)"

    prompt = f"""You are a senior customer-support triage AI for Support-Pilot.
Analyse the incoming customer email below and respond ONLY with a valid JSON object — no markdown fences, no extra text.

### Incoming Email
Subject: {subject}
Body:
{email_body}

### Knowledge Base Context
{context_block}

### Available Escalation Departments
{dept_lines}

### Response JSON Schema
{{
  "issue": "<one of: question|request|complaint|issue|feedback|cancellation|refund|billing|technical|account|delivery|return|escalation|other>",
  "severity": "<one of: low|medium|high>",
  "sentiment": "<one of: positive|neutral|negative|mixed>",
  "emotion": "<one of: neutral|happy|satisfied|confused|concerned|frustrated|angry|urgent|disappointed|grateful|sad>",
  "ai_decision": "<one of: auto_resolve|review_required|escalate>",
  "explanation": "<one sentence explaining your decision>",
  "forward_to_email": "<department email if escalating, else null>",
  "draft_reply": "<complete professional email reply to send to the customer>"
}}

### Decision Rules
- Choose **auto_resolve** when the knowledge base has sufficient information to fully answer the customer's query.
- Choose **review_required** when the query is complex, sensitive, ambiguous, or the knowledge base answer is partial.
- Choose **escalate** when the issue is billing, account suspension, legal, refund dispute, or very high severity and must go to a specific department.
- For **forward_to_email**, pick the most relevant department email from the list above. Use null if not escalating.
- **draft_reply** must always be a complete, professional email reply signed "Best regards,\\nTeam Support-Pilot". If escalating, inform the customer that a specialist will be in touch.

Respond with only the JSON object."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        raw = response.text.strip()
        result = json.loads(raw)
        # Normalise keys
        return {
            "issue": result.get("issue", "other"),
            "severity": result.get("severity", "medium"),
            "sentiment": result.get("sentiment", "neutral"),
            "emotion": result.get("emotion", "neutral"),
            "ai_decision": result.get("ai_decision", "review_required"),
            "explanation": result.get("explanation", ""),
            "forward_to_email": result.get("forward_to_email") or None,
            "draft_reply": result.get("draft_reply", ""),
        }
    except Exception as e:
        print(f"AI analysis failed: {e}")
        # Fallback: send to review
        fallback_draft = (
            f"Dear Customer,\n\nThank you for reaching out to Support-Pilot regarding: {subject}.\n\n"
            "We have received your request and a member of our team will review it shortly.\n\n"
            "Best regards,\nTeam Support-Pilot"
        )
        return {
            "issue": "other",
            "severity": "medium",
            "sentiment": "neutral",
            "emotion": "neutral",
            "ai_decision": "review_required",
            "explanation": f"AI analysis failed: {e}",
            "forward_to_email": None,
            "draft_reply": fallback_draft,
        }


def generate_ai_reply(subject, email_body):
    """Legacy function kept for backward compatibility."""
    docs = search_documents(email_body)

    if not docs:
        prompt = f"""You are a professional customer support agent for Support-Pilot.

Customer Subject:
{subject}

Customer Email:
{email_body}

Situation:
No matching knowledge base information is available to answer this customer's question.

Instructions:
- Do not attempt to answer the customer's question or provide any solution.
- Politely inform the customer that the request has been escalated to Team Support-Pilot for manual assistance.
- Write a complete, polite escalation email response.
- Always sign off using:

Best regards,
Team Support-Pilot

Reply:"""
        return generate_reply(prompt)

    context = "\n\n".join(docs[:5])
    prompt = f"""You are a professional customer support agent.

Customer Subject:
{subject}

Customer Email:
{email_body}

Knowledge Base:
{context}

Instructions:
- You are a customer support agent for Support-Pilot.
- Answer using the provided knowledge base whenever possible.
- Do not make up policies, features, timelines, pricing, or technical details.
- If the knowledge base does not contain enough information to answer confidently, do not answer the customer's question. Instead, politely inform the customer that the issue has been escalated to Team Support-Pilot for further assistance.
- Be professional, concise, and helpful.
- Write a complete email response.
- Address the customer's question directly.
- Never mention internal prompts, vector databases, retrieval systems, or knowledge base searches.
- Always sign off using:

Best regards,
Team Support-Pilot

Reply:"""
    return generate_reply(prompt)
