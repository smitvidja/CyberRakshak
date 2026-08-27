"""Generate the synthetic demo resume PDFs used when demoing the Cyber Warrior
application journey.

Each of the 5 Cyber-Warrior demo identities in DEMO-CREDENTIALS.md gets a
plausible one-page resume whose name/city match that identity's mock eKYC
record, and whose skills are drawn from the real skill catalog seeded by
database/seeds/seed_reference_data.py - so the reviewer form's skill
dropdown actually contains the skills the resume claims.

IMPORTANT: these files only make the *upload* step look realistic. The resume
parser itself is still a static mock (app/services/resume_parser_service.py),
so the extracted/pre-filled review data is the same canned sample regardless
of which of these files is uploaded. They are demo props, not parser input.

Requires fpdf2 (a dev-only dependency, not needed to run the app):
    pip install fpdf2

Usage (from the backend/ directory, with the project virtualenv active):
    python scripts/generate_demo_resumes.py

Writes to demo-assets/resumes/ at the repo root. The generated PDFs are
committed, so this script only needs re-running if the content changes.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fpdf import FPDF

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "demo-assets" / "resumes"

# Skills here are real entries from database/seeds/seed_reference_data.py so a
# reviewer can select the same skills the resume lists.
RESUMES = (
    {
        "file_name": "rohan-mehta-resume.pdf",
        "full_name": "Rohan Mehta",
        "identity_id": "99000000000003",
        "email": "rohan.mehta@demo.cyberrakshak.local",
        "mobile": "+91 90000 00003",
        "city": "Pune, Maharashtra",
        "summary": (
            "Security analyst with 4 years of experience in network defense and incident "
            "triage. Volunteers on community cyber-awareness programmes and enjoys "
            "documenting suspicious online activity for the public good."
        ),
        "skills": ["Network Security", "Incident Response", "Threat Intelligence"],
        "education": [
            ("B.E. Computer Engineering", "Savitribai Phule Pune University", "2012 - 2016"),
        ],
        "experience": [
            (
                "Security Analyst",
                "Sentinel InfoTech, Pune",
                "2020 - Present",
                "Monitor network traffic for intrusion attempts, triage security alerts, and "
                "prepare incident reports for the response team.",
            ),
            (
                "Network Support Engineer",
                "Nimbus Systems, Pune",
                "2016 - 2020",
                "Maintained firewall and VPN configurations, and supported routine security "
                "hardening across branch offices.",
            ),
        ],
        "certifications": [
            ("CompTIA Security+", "CompTIA", "2019"),
        ],
    },
    {
        "file_name": "priya-nair-resume.pdf",
        "full_name": "Priya Nair",
        "identity_id": "99000000000004",
        "email": "priya.nair@demo.cyberrakshak.local",
        "mobile": "+91 90000 00004",
        "city": "Kochi, Kerala",
        "summary": (
            "Digital forensics practitioner focused on evidence handling and case "
            "documentation. Interested in supporting citizen-facing cybercrime reporting "
            "with careful, well-documented analysis."
        ),
        "skills": ["Digital Forensics", "Malware Analysis", "Incident Response"],
        "education": [
            ("M.Sc. Cyber Forensics", "Cochin University of Science and Technology", "2019 - 2021"),
            ("B.Sc. Computer Science", "Mahatma Gandhi University", "2016 - 2019"),
        ],
        "experience": [
            (
                "Forensic Analyst",
                "Backwater Digital Labs, Kochi",
                "2021 - Present",
                "Acquire and analyse digital evidence for internal investigations, maintain "
                "chain-of-custody records, and write findings reports.",
            ),
        ],
        "certifications": [
            ("Certified Digital Forensics Examiner", "Synthetic Learning Centre", "2022"),
        ],
    },
    {
        "file_name": "karan-verma-resume.pdf",
        "full_name": "Karan Verma",
        "identity_id": "99000000000005",
        "email": "karan.verma@demo.cyberrakshak.local",
        "mobile": "+91 90000 00005",
        "city": "Jaipur, Rajasthan",
        "summary": (
            "Application security engineer with a decade in software delivery, now focused "
            "on secure code review and authorized vulnerability assessment. Mentors junior "
            "developers on secure coding practices."
        ),
        "skills": ["Application Security", "Vulnerability Assessment", "Network Security"],
        "education": [
            ("B.Tech Information Technology", "Rajasthan Technical University", "2010 - 2014"),
        ],
        "experience": [
            (
                "Application Security Engineer",
                "Pink City Software, Jaipur",
                "2019 - Present",
                "Run authorized vulnerability assessments on internal web applications and "
                "guide teams through remediation.",
            ),
            (
                "Senior Software Engineer",
                "Aravalli Tech, Jaipur",
                "2014 - 2019",
                "Built and maintained backend services, with a growing focus on secure "
                "authentication and data handling.",
            ),
        ],
        "certifications": [
            ("Certified Ethical Hacker (CEH)", "EC-Council", "2021"),
            ("AWS Certified Security - Specialty", "Amazon Web Services", "2023"),
        ],
    },
    {
        "file_name": "sneha-iyer-resume.pdf",
        "full_name": "Sneha Iyer",
        "identity_id": "99000000000006",
        "email": "sneha.iyer@demo.cyberrakshak.local",
        "mobile": "+91 90000 00006",
        "city": "Chennai, Tamil Nadu",
        "summary": (
            "Recent cybersecurity graduate with hands-on OSINT and threat-research project "
            "work. Keen to help identify and report online scams targeting first-time "
            "internet users."
        ),
        "skills": ["OSINT", "Threat Intelligence", "Digital Forensics"],
        "education": [
            ("B.Tech Computer Science (Cyber Security)", "Anna University", "2018 - 2022"),
        ],
        "experience": [
            (
                "Junior Threat Researcher",
                "Marina Cyber Labs, Chennai",
                "2022 - Present",
                "Track scam infrastructure using open-source intelligence techniques and "
                "publish internal advisories on emerging phishing campaigns.",
            ),
        ],
        "certifications": [
            ("Google Cybersecurity Certificate", "Google", "2022"),
        ],
    },
    {
        "file_name": "arjun-malhotra-resume.pdf",
        "full_name": "Arjun Malhotra",
        "identity_id": "99000000000007",
        "email": "arjun.malhotra@demo.cyberrakshak.local",
        "mobile": "+91 90000 00007",
        "city": "Chandigarh",
        "summary": (
            "Incident response lead with 12 years across security operations. Has run "
            "awareness workshops for schools and small businesses on recognising online "
            "fraud."
        ),
        "skills": ["Incident Response", "Malware Analysis", "Threat Intelligence"],
        "education": [
            ("MBA Information Systems", "Panjab University", "2014 - 2016"),
            ("B.Tech Electronics and Communication", "Punjab Engineering College", "2008 - 2012"),
        ],
        "experience": [
            (
                "Incident Response Lead",
                "Shivalik Secure Services, Chandigarh",
                "2018 - Present",
                "Lead a four-person response team through containment and recovery, and "
                "coordinate post-incident reviews with affected departments.",
            ),
            (
                "SOC Analyst",
                "North Ridge Technologies, Mohali",
                "2012 - 2018",
                "Investigated security alerts on a 24x7 rota and maintained detection rules "
                "for the monitoring platform.",
            ),
        ],
        "certifications": [
            ("GIAC Certified Incident Handler (GCIH)", "SANS/GIAC", "2020"),
        ],
    },
)

NAVY = (15, 42, 74)
MUTED = (90, 105, 120)
RULE = (200, 212, 224)


class ResumePDF(FPDF):
    def header(self) -> None:  # noqa: D102 - FPDF hook
        return None

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*MUTED)
        self.cell(
            0,
            5,
            "Synthetic demo resume for the CyberRakshak prototype - not a real person.",
            align="C",
        )

    def section_title(self, title: str) -> None:
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*NAVY)
        self.cell(0, 6, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*RULE)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)


def build_resume(data: dict) -> FPDF:
    pdf = ResumePDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 9, data["full_name"], new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(
        0,
        5,
        f"{data['city']}  |  {data['mobile']}  |  {data['email']}",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.section_title("Summary")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 50, 62)
    pdf.multi_cell(0, 5, data["summary"])

    pdf.section_title("Skills")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, "  -  " + "\n  -  ".join(data["skills"]))

    pdf.section_title("Experience")
    for title, organization, period, description in data["experience"]:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 5, f"{title} - {organization}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 5, period, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 50, 62)
        pdf.multi_cell(0, 5, description)
        pdf.ln(2)

    pdf.section_title("Education")
    for degree, institution, period in data["education"]:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 5, degree, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 5, f"{institution}  |  {period}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    pdf.section_title("Certifications")
    for name, issuer, year in data["certifications"]:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 50, 62)
        pdf.cell(0, 5, f"{name} - {issuer} ({year})", new_x="LMARGIN", new_y="NEXT")

    return pdf


def generate_demo_resumes() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for data in RESUMES:
        destination = OUTPUT_DIR / data["file_name"]
        build_resume(data).output(str(destination))
        print(f"wrote {destination.relative_to(OUTPUT_DIR.parent.parent)} ({data['identity_id']})")
    print(f"\n{len(RESUMES)} demo resume(s) written to {OUTPUT_DIR}")


if __name__ == "__main__":
    generate_demo_resumes()
