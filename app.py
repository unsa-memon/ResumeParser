from flask import Flask, render_template, request
import re
import os
import matplotlib.pyplot as plt
import PyPDF2
import docx
from fuzzywuzzy import process

app = Flask(__name__)

# Master Skill List for Extraction
master_skill_list = [
    # Programming Languages
    "python", "java", "c++", "c", "c#", "javascript", "typescript", 
    "ruby", "php", "swift", "kotlin", "go", "rust", "scala", "r", 
    "dart", "perl", "bash", "sql",

    # Web Development
    "html", "css", "react", "angular", "vue", "django", "flask", 
    "spring", "laravel", "node.js", "express", "jquery", "bootstrap",
    "sass", "less", "tailwind", "redux", "graphql", "rest api", "react.js",

    # Mobile Development
    "android", "ios", "flutter", "react native", "xamarin",

    # Databases
    "mysql", "postgresql", "oracle", "sqlite", "mongodb", "redis", 
    "firebase", "cassandra", "mariadb", "elasticsearch",

    # DevOps & Cloud
    "aws", "azure", "google cloud", "docker", "kubernetes", "jenkins", 
    "ansible", "terraform", "github actions", "gitlab ci", "nginx", 
    "apache", "linux", "windows server",

    # Data Science & AI
    "machine learning", "deep learning", "tensorflow", "pytorch", 
    "keras", "opencv", "numpy", "pandas", "scikit-learn", "matplotlib", 
    "seaborn", "spark", "hadoop", "tableau", "power bi", "data science",

    # Version Control & Tools
    "git", "github", "gitlab", "bitbucket", "svn", "mercurial",
    "jira", "trello", "confluence", "slack", "docker", "postman",

    # Testing
    "selenium", "jest", "mocha", "junit", "pytest", "cypress",

    # Cybersecurity
    "ethical hacking", "penetration testing", "owasp", "kali linux",
    "metasploit", "burp suite", "siem", "splunk",

    # Methodologies
    "agile", "scrum", "kanban", "devops", "ci/cd", "tdd", "bdd",

    # Other IT Skills
    "data structures", "algorithms", "oop", "functional programming",
    "microservices", "serverless", "blockchain", "solidity",
    "arduino", "raspberry pi", "embedded systems","networking"
]


# Synonym Dictionary
synonym_dict = {
    "machine learning": ["ml", "deep learning", "artificial intelligence"],
    "data scientist": ["data science", "research scientist"],
    "nlp": ["natural language processing"],
    "sql": ["structured query language", "database management"],
    "python": ["py"],
}

# Function to Extract Text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text.lower()

# Function to Extract Text from DOCX
def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.lower()


# Function to Extract Name from Email
def extract_name_from_email(email):
    """Extract first and last name from email, handling cases with numbers or extra info."""
    if email == "Not Found":
        return "Not Found"
    
    # Extract prefix before '@'
    prefix = email.split("@")[0]
    
    # Remove numbers from the prefix (e.g., 'bscsf22' becomes 'bscsf')
    prefix = re.sub(r'\d+', '', prefix)
    
    # Remove possible domain-like info (e.g., 'bscsf22' should be removed leaving 'Umairahmed')
    prefix = re.sub(r'\b[a-zA-Z]{2,}\d{2,}\b', '', prefix).strip()

    # Split by underscores or dots to separate potential first and last names
    parts = re.split(r"[._]", prefix)
    
    # Capitalize each part and join with spaces
    name_parts = [part.capitalize() for part in parts if part]
    
    # If the name has a single part, assume it's the first name (like 'umair')
    if len(name_parts) == 1:
        name = name_parts[0]
    else:
        # Assume the first part is the first name and avoid extra info
        name = name_parts[0]  # Take the first part for the name (like 'Umairahmed')
    
    return name if name else "Not Found"


# Function to Extract Resume Info
def extract_resume_info(text):
    # Email Extraction (key for name)
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    email = email_match.group(0) if email_match else "Not Found"

    # Name Extraction (priority: email > first line)
    name = extract_name_from_email(email)
    if name == "Not Found":
        # Fallback: First two capitalized words in the first line
        first_line = text.split("\n")[0].strip()
        words = [word for word in first_line.split() if word[0].isupper()]
        name = " ".join(words[:2]) if len(words) >= 2 else "Not Found"

    # Phone Extraction (enhanced pattern for international formats)
    phone_match = re.search(r"\(?\+?\d{1,4}?\)?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,4}", text)
    phone = phone_match.group(0) if phone_match else "Not Found"

    # Skills Extraction (check for skills in the master list)
    words = re.findall(r"\b[a-zA-Z0-9\+\#]+\b", text.lower())
    skills = {word for word in words if word in master_skill_list}

    return name, email, phone, address, skills


# Function to Normalize Resume Skills
def normalize_skills(resume_skills):
    normalized_resume_skills = set()
    for skill in resume_skills:
        matched = False
        for key, synonyms in synonym_dict.items():
            if skill in synonyms or skill == key:
                normalized_resume_skills.add(key)
                matched = True
                break
        if not matched:
            normalized_resume_skills.add(skill)
    return normalized_resume_skills

# Function for Strict Fuzzy Matching
def fuzzy_match(skill, job_keywords, threshold=90):
    match, score = process.extractOne(skill, job_keywords)
    return match if score >= threshold else None

# Function to Process Resume
def process_resume(resume_path, job_keywords):
    if resume_path.endswith(".pdf"):
        resume_text = extract_text_from_pdf(resume_path)
    elif resume_path.endswith(".docx"):
        resume_text = extract_text_from_docx(resume_path)
    else:
        return None, None, None, None, None, None, None

    # Extract information from resume
    name, email, phone, address, resume_skills = extract_resume_info(resume_text)
    
    # Normalize skills using synonyms
    normalized_resume_skills = normalize_skills(resume_skills)
    final_matched_skills = set()

    # Database skills that should be matched explicitly
    database_skills = {"mysql", "postgresql", "oracle", "SQL"}

    # Match skills using fuzzy matching
    for skill in normalized_resume_skills:
        if skill in database_skills:
            if any(db in job_keywords for db in database_skills):
                final_matched_skills.add(skill)
        else:
            best_match = fuzzy_match(skill, job_keywords)
            if best_match:
                final_matched_skills.add(best_match)

    # Calculate match percentage
    match_percentage = round((len(final_matched_skills) / len(job_keywords)) * 100, 2)
    missing_skills = set(job_keywords) - final_matched_skills

    # Generate Visualization
    generate_visualization(final_matched_skills, missing_skills, match_percentage)

    return name, email, phone, address, final_matched_skills, match_percentage, missing_skills

# Function to Generate Visualizations (Bar and Pie charts)
def generate_visualization(matched_skills, missing_skills, match_percentage):
    # Use Agg backend to avoid GUI interaction errors
    plt.switch_backend('Agg')

    matched_skills = sorted(list(matched_skills))  # sort matched skills alphabetically
    missing_skills = sorted(list(missing_skills))  # sort missing skills alphabetically

    skills = matched_skills + missing_skills
    presence = [1] * len(skills)
    colors = ["green"] * len(matched_skills) + ["red"] * len(missing_skills)

    # Bar Chart
    plt.figure(figsize=(10, 6))
    plt.bar(skills, presence, color=colors)
    plt.xlabel("Skills")
    plt.ylabel("Presence")
    plt.title("Matched & Missing Skills (Matched First)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig("static/bar_chart.png")
    plt.close()

    # Pie Chart
    plt.figure(figsize=(5, 5))
    plt.pie(
        [match_percentage, 100 - match_percentage],
        labels=["Matched", "Not Matched"],
        colors=["green", "red"],
        autopct="%1.1f%%",
        startangle=140
    )
    plt.title("Resume Match Percentage")
    plt.savefig("static/pie_chart.png")
    plt.close()

# Flask Route
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        job_keywords = request.form["job_description"].lower().split(",")
        job_keywords = [keyword.strip() for keyword in job_keywords]
        file = request.files["resume"]
        if file:
            filepath = os.path.join("uploads", file.filename)
            file.save(filepath)
            name, email, phone, address, matched_skills, match_percentage, missing_skills = process_resume(filepath, job_keywords)
            os.remove(filepath)
            return render_template("result.html", name=name, email=email, phone=phone, address=address, skills=matched_skills, percentage=match_percentage)
    return render_template("index.html")

if __name__ == "__main__":
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.run(debug=True)





