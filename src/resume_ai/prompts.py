# Prompt templates for Google LLM (placeholders)

KEYWORD_EXTRACTION_PROMPT = (
    "You are an expert technical recruiter and resume strategist.\n"
    "Task: From the following job description, extract 30-50 role-specific keywords, including:\n"
    "- Required hard skills (languages, frameworks, platforms, tools)\n"
    "- Preferred skills (mark as preferred)\n"
    "- Domain terms and responsibilities\n"
    "- Seniority and leadership signals\n"
    "Rules:\n"
    "- Preserve exact phrasing used in the JD where possible.\n"
    "- Include common synonyms (e.g., 'LLM' and 'Large Language Model').\n"
    "- Return JSON with fields: required[], preferred[], verbs[], domains[].\n"
    "- Do not include soft, generic words (e.g., team player).\n\n"
    "JD:\n{jd_text}\n"
)

BULLET_REWRITE_PROMPT = (
    "You are an expert resume writer. Rewrite bullets using CAR (Context-Action-Result).\n"
    "Constraints:\n"
    "- Use strong action verbs; keep accurate and concise (max 24 words per bullet).\n"
    "- Integrate 2-3 target keywords naturally; avoid keyword stuffing.\n"
    "- Use present tense for current role; past tense otherwise.\n"
    "- Quantify outcomes with conservative metrics; if unknown, propose placeholders clearly marked with <>.\n"
    "- Return JSON with bullets[] (4-6 bullets).\n\n"
    "Input experience (JSON):\n{experience_json}\n\n"
    "Target keywords:\n{keywords}\n"
)

SUMMARY_PROMPT = (
    "Create a 2-3 line resume summary tailored to the target role and company.\n"
    "Constraints:\n"
    "- Mirror terminology from the job description.\n"
    "- Highlight top 3-5 hard skills and 1-2 quantified outcomes.\n"
    "- Avoid first-person and fluff; be factual and concise.\n"
    "- Return plain text only.\n\n"
    "Role: {role}\nCompany: {company}\nTop keywords: {keywords}\n"
)
