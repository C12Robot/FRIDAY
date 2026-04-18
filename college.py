import os
import json
import csv
import requests
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

OBSIDIAN_BASE    = r"C:\Users\meena\Documents\Builder_Brain"
ASSIGNMENTS_FILE = os.path.join(os.path.dirname(__file__), "assignments.json")
TESSERACT_PATH   = r"C:\Program Files\Tesseract-OCR\tesseract.exe"



def read_any_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".pdf":
            return _read_pdf(filepath)
        elif ext in (".docx", ".doc"):
            return _read_docx(filepath)
        elif ext == ".txt" or ext == ".md":
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        elif ext == ".csv":
            return _read_csv(filepath)
        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
            return _read_image(filepath)
        else:
            return f"Unsupported file type: {ext}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


def _read_pdf(filepath):
    import fitz
    doc  = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text[:10000]


def _read_docx(filepath):
    from docx import Document
    doc   = Document(filepath)
    lines = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(lines)[:10000]


def _read_csv(filepath):
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            rows.append(", ".join(row))
            if i > 100:
                rows.append("... (truncated)")
                break
    return "\n".join(rows)


def _read_image(filepath):
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    img  = Image.open(filepath)
    text = pytesseract.image_to_string(img)
    return text[:5000]



def summarise_file(filepath):
    content = read_any_file(filepath)
    if content.startswith("Error") or content.startswith("Unsupported"):
        return content

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system="You summarise academic documents for a computer engineering student. Extract key concepts, important points and any formulas or definitions. Be concise and structured. Use bullet points.",
        messages=[{"role": "user", "content": f"Summarise this:\n\n{content}"}]
    )
    return response.content[0].text.strip()


def summarise_text(text):
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system="You summarise academic content for a computer engineering student. Extract key concepts, important points and definitions. Be concise and structured.",
        messages=[{"role": "user", "content": f"Summarise:\n\n{text}"}]
    )
    return response.content[0].text.strip()



def generate_quiz(filepath=None, text=None, num_questions=5):
    content = text
    if filepath:
        content = read_any_file(filepath)
    if not content:
        return "No content to generate quiz from."

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system=f"""Generate {num_questions} quiz questions for a computer engineering student.
        Mix of MCQ and short answer. For MCQ include 4 options and mark the correct one.
        Format clearly with Q1, Q2 etc. Cover the most important concepts.""",
        messages=[{"role": "user", "content": f"Generate quiz from:\n\n{content[:5000]}"}]
    )
    return response.content[0].text.strip()



def _load_assignments():
    if not os.path.exists(ASSIGNMENTS_FILE):
        return []
    with open(ASSIGNMENTS_FILE, "r") as f:
        return json.load(f)

def _save_assignments(data):
    with open(ASSIGNMENTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_assignment(title, due_date, subject=""):
    data = _load_assignments()
    data.append({
        "title":    title,
        "subject":  subject,
        "due_date": due_date,
        "added":    datetime.now().strftime("%Y-%m-%d"),
        "done":     False
    })
    _save_assignments(data)
    return f"Assignment added: {title} — due {due_date}"

def get_assignments():
    data = _load_assignments()
    if not data:
        return "No assignments tracked yet."
    pending = [a for a in data if not a["done"]]
    if not pending:
        return "All assignments completed!"
    lines = ["Pending assignments:"]
    for a in sorted(pending, key=lambda x: x["due_date"]):
        subj = f" ({a['subject']})" if a["subject"] else ""
        lines.append(f"- {a['title']}{subj} — due {a['due_date']}")
    return "\n".join(lines)

def mark_assignment_done(title):
    data = _load_assignments()
    for a in data:
        if title.lower() in a["title"].lower():
            a["done"] = True
            _save_assignments(data)
            return f"Marked done: {a['title']}"
    return f"Assignment not found: {title}"



def find_research_papers(topic):
    try:
        url     = "https://api.tavily.com/search"
        headers = {
            "Authorization": f"Bearer {os.getenv('TAVILY_API_KEY')}",
            "Content-Type": "application/json"
        }
        r = requests.post(url, headers=headers, json={
            "query": f"{topic} research paper arxiv academic",
            "search_depth": "basic",
            "max_results": 5
        })
        results = r.json().get("results", [])
        if not results:
            return "No papers found."

        papers = []
        for res in results:
            papers.append(f"- {res.get('title', 'Unknown')}\n  {res.get('url', '')}\n  {res.get('content', '')[:150]}")

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            system="Summarise these research paper results for a computer engineering student. List the most relevant ones with a one-line description of what each covers.",
            messages=[{"role": "user", "content": "\n\n".join(papers)}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Paper search error: {str(e)}"



def explain_concept(concept, level="normal"):
    level_prompts = {
        "simple": "Explain like I'm 5. Use a simple real-world analogy.",
        "normal": "Explain clearly for a computer engineering student. Cover what it is, why it matters, and a simple example.",
        "deep":   "Give a deep technical explanation with implementation details, complexity analysis if applicable, and real-world use cases."
    }
    system_prompt = f"""You are a computer engineering tutor specialising in:
    DSA, Operating Systems, Computer Networks, DBMS, Computer Architecture, Algorithms, OOP, Theory of Computation.
{level_prompts.get(level, level_prompts['normal'])}"""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        system=system_prompt,
        messages=[{"role": "user", "content": f"Explain: {concept}"}]
    )
    return response.content[0].text.strip()