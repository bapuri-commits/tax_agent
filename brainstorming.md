You are a senior backend architect and AI system designer.

We are building an upgraded AI-powered KakaoTalk civil service chatbot for Seongbuk-gu District Office.

Ignore any existing project files.
Design this from scratch with a cost-efficient, production-ready architecture.

--------------------------------------------------
🎯 PROJECT GOAL
--------------------------------------------------

Build a KakaoTalk chatbot that behaves like a real civil service consultant.

When a citizen speaks in natural language, the system must:

1. Understand the civil complaint intent
2. Collect only the minimum required additional information (2–4 short questions)
3. Determine the user’s case
4. Provide:
   - Clear conclusion
   - Required documents
   - Application channel (online/offline)
   - Official links
   - Responsible department info
   - Next action buttons
5. If uncertain → safely route to human department

This must feel structured, official, and reliable.

No hallucination.
Always attach official links (via RAG).

--------------------------------------------------
🏗 SYSTEM ARCHITECTURE REQUIREMENTS
--------------------------------------------------

Design a cost-efficient hybrid architecture:

Layer 1: Kakao OpenBuilder
- Entry UI
- Category buttons
- Consent
- Basic form inputs
- Callback integration

Layer 2: Backend Server (FastAPI preferred)
Responsibilities:
- Session management
- Civil complaint intent classification
- Playbook-driven decision logic
- Minimal LLM usage
- RAG retrieval
- Structured response formatting
- Escalation logic

Layer 3: Knowledge System (RAG)
- Index Seongbuk-gu official pages, FAQs, PDFs
- Use pgvector (Postgres)
- Always return 1–3 official source links

Layer 4: LLM Usage Policy
LLM must only be used for:
- Intent classification
- Generating concise follow-up questions
- Polishing final structured response

LLM must NOT:
- Invent policy details
- Replace rule-based decision logic

--------------------------------------------------
📦 MVP SCOPE (PHASE 1)
--------------------------------------------------

Define Top 30 assumed high-frequency civil complaints such as:
- Parking violations
- Resident registration (move-in)
- Welfare eligibility
- Local tax
- Childcare
- Certificates
- Garbage disposal
- Construction complaints

For each complaint type:
Create a Playbook JSON structure including:

{
  id,
  name,
  required_slots: [],
  decision_rules: [],
  required_documents: [],
  official_links: [],
  department_info: {},
  next_actions: []
}

Design this schema clearly.

--------------------------------------------------
🧠 SESSION + STATE DESIGN
--------------------------------------------------

Design database schema:

users
sessions
complaint_cases
slot_values
conversation_logs

Explain how state transitions work.

Design a state machine:
- INTENT_DETECTED
- SLOT_FILLING
- CASE_DETERMINED
- RESPONSE_READY
- ESCALATED

--------------------------------------------------
🔍 RAG PIPELINE DESIGN
--------------------------------------------------

Explain:
- Document ingestion
- HTML/PDF parsing
- Chunking strategy
- Embedding storage
- Retrieval flow
- Citation enforcement in final answer

--------------------------------------------------
💰 COST OPTIMIZATION STRATEGY
--------------------------------------------------

Design clear rules:
- When LLM is called
- When rule engine handles response
- Token control strategy
- Fallback path
- Estimated monthly cost model (small-scale municipal traffic)

--------------------------------------------------
📤 RESPONSE TEMPLATE FORMAT
--------------------------------------------------

Every chatbot answer must follow:

✅ Conclusion  
📌 What you need now (checklist)  
📄 Required documents  
🔗 Official links  
🏢 Responsible department  
➡ Next action buttons  

Design a function that formats output consistently.

--------------------------------------------------
📁 OUTPUT REQUIREMENTS
--------------------------------------------------

1. Full system architecture diagram (text form)
2. Backend folder structure
3. Database schema
4. Playbook schema definition
5. Example playbook for "Resident Move-in 신고"
6. RAG pipeline explanation
7. LLM integration logic pseudocode
8. State machine logic
9. API endpoint definitions
10. Sample response JSON

Design this like a real production blueprint.

Focus on clarity, maintainability, and low operating cost.

Do NOT write marketing text.
Write like an engineer designing a municipal system.