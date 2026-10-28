from pathlib import Path
import csv
import statistics
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
    Table,
    TableStyle,
    KeepTogether,
)

# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent

DATA_PATH = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "ai_student_impact_processed.csv"
)

IMAGE_DIR = PROJECT_DIR / "images" / "visualizations"
REPORT_DIR = PROJECT_DIR / "reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

PDF_PATH = REPORT_DIR / "EDA-REPORT.pdf"


# ============================================================
# 2. LOAD PROCESSED DATASET
# ============================================================

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Processed dataset not found:\n{DATA_PATH}"
    )

with open(DATA_PATH, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)
    columns = reader.fieldnames or []
    rows = list(reader)

if not rows:
    raise ValueError("The processed dataset is empty.")

print("=" * 60)
print("AI-STUDENT-INSIGHTS: EDA REPORT GENERATOR")
print("=" * 60)

print(f"Dataset: {DATA_PATH}")
print(f"Rows: {len(rows):,}")
print(f"Columns: {len(columns)}")


# ============================================================
# 3. DATASET VALIDATION
# ============================================================

missing_cells = sum(
    1
    for row in rows
    for column in columns
    if row.get(column) is None
    or row.get(column).strip() == ""
)

duplicate_rows = len(rows) - len(
    {
        tuple(row.get(column, "") for column in columns)
        for row in rows
    }
)

required_columns = [
    "Pre_Semester_GPA",
    "Post_Semester_GPA",
    "Weekly_GenAI_Hours",
    "Traditional_Study_Hours",
    "Perceived_AI_Dependency",
    "Anxiety_Level_During_Exams",
    "Skill_Retention_Score",
    "Burnout_Risk_Level",
    "AI_Usage_Group",
]

missing_columns = [
    column
    for column in required_columns
    if column not in columns
]

if missing_columns:
    raise ValueError(
        "Required columns are missing: "
        + ", ".join(missing_columns)
    )

if "Student_ID" in columns:
    print(
        "WARNING: Student_ID is present in the processed dataset."
    )

if "AI_Use_Group" in columns:
    print(
        "WARNING: Unused AI_Use_Group column is present."
    )


# ============================================================
# 4. NUMERICAL ANALYSIS
# ============================================================

def get_numeric_values(column):
    """Return valid numeric values from a dataset column."""
    values = []

    for row in rows:
        try:
            value = float(row[column])

            if value == value:  # Exclude NaN
                values.append(value)

        except (ValueError, TypeError, KeyError):
            continue

    return values


def mean_value(column):
    values = get_numeric_values(column)
    return statistics.mean(values) if values else None


def median_value(column):
    values = get_numeric_values(column)
    return statistics.median(values) if values else None


def standard_deviation(column):
    values = get_numeric_values(column)

    if len(values) < 2:
        return None

    return statistics.stdev(values)


def format_number(value, digits=2):
    if value is None:
        return "N/A"

    return f"{value:,.{digits}f}"


pre_gpa = get_numeric_values("Pre_Semester_GPA")
post_gpa = get_numeric_values("Post_Semester_GPA")

gpa_differences = [
    post - pre
    for pre, post in zip(pre_gpa, post_gpa)
]

improved = sum(value > 0 for value in gpa_differences)
unchanged = sum(value == 0 for value in gpa_differences)
declined = sum(value < 0 for value in gpa_differences)

paired_count = len(gpa_differences)

mean_gpa_change = (
    statistics.mean(gpa_differences)
    if gpa_differences
    else None
)

gpa_improved_pct = (
    improved / paired_count * 100
    if paired_count
    else 0
)

gpa_unchanged_pct = (
    unchanged / paired_count * 100
    if paired_count
    else 0
)

gpa_declined_pct = (
    declined / paired_count * 100
    if paired_count
    else 0
)


# ============================================================
# 5. CATEGORICAL DISTRIBUTIONS
# ============================================================

def category_counts(column):
    counts = {}

    for row in rows:
        value = row.get(column, "").strip()
        counts[value] = counts.get(value, 0) + 1

    return sorted(
        counts.items(),
        key=lambda item: item[1],
        reverse=True,
    )


ai_group_counts = category_counts("AI_Usage_Group")
burnout_counts = category_counts("Burnout_Risk_Level")
major_counts = (
    category_counts("Major_Category")
    if "Major_Category" in columns
    else []
)


# ============================================================
# 6. CORRELATIONS
# ============================================================

def pearson_correlation(column_x, column_y):
    """Calculate Pearson correlation using paired numeric values."""

    pairs = []

    for row in rows:
        try:
            x = float(row[column_x])
            y = float(row[column_y])

            if x == x and y == y:
                pairs.append((x, y))

        except (ValueError, TypeError, KeyError):
            continue

    if len(pairs) < 2:
        return None

    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]

    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)

    numerator = sum(
        (x - mean_x) * (y - mean_y)
        for x, y in pairs
    )

    denominator_x = sum(
        (x - mean_x) ** 2
        for x in xs
    )

    denominator_y = sum(
        (y - mean_y) ** 2
        for y in ys
    )

    denominator = (denominator_x * denominator_y) ** 0.5

    if denominator == 0:
        return None

    return numerator / denominator


correlation_pairs = [
    (
        "Pre_Semester_GPA",
        "Post_Semester_GPA",
        "Pre-semester GPA vs. post-semester GPA",
    ),
    (
        "Weekly_GenAI_Hours",
        "Perceived_AI_Dependency",
        "Weekly AI usage vs. perceived AI dependency",
    ),
    (
        "Perceived_AI_Dependency",
        "Anxiety_Level_During_Exams",
        "Perceived AI dependency vs. exam anxiety",
    ),
    (
        "Weekly_GenAI_Hours",
        "Anxiety_Level_During_Exams",
        "Weekly AI usage vs. exam anxiety",
    ),
    (
        "Weekly_GenAI_Hours",
        "Traditional_Study_Hours",
        "Weekly AI usage vs. traditional study hours",
    ),
    (
        "Weekly_GenAI_Hours",
        "Post_Semester_GPA",
        "Weekly AI usage vs. post-semester GPA",
    ),
]


# ============================================================
# 7. REPORT STYLES
# ============================================================

styles = getSampleStyleSheet()

styles.add(
    ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=25,
        leading=32,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#163A5F"),
        spaceAfter=18,
    )
)

styles.add(
    ParagraphStyle(
        name="SubtitleCustom",
        parent=styles["Normal"],
        fontSize=13,
        leading=19,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#526579"),
        spaceAfter=12,
    )
)

styles.add(
    ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading1"],
        fontSize=17,
        leading=22,
        textColor=colors.HexColor("#163A5F"),
        spaceBefore=12,
        spaceAfter=10,
        keepWithNext=True,
    )
)

styles.add(
    ParagraphStyle(
        name="SubHeadingCustom",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#246B8E"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True,
    )
)

styles.add(
    ParagraphStyle(
        name="BodyCustom",
        parent=styles["BodyText"],
        fontSize=9,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=8,
    )
)

styles.add(
    ParagraphStyle(
        name="SmallCustom",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#526579"),
        spaceAfter=5,
    )
)

styles.add(
    ParagraphStyle(
        name="CoverDetails",
        parent=styles["Normal"],
        fontSize=11,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#35495E"),
    )
)


# ============================================================
# 8. PDF HEADER AND FOOTER
# ============================================================

def add_page_number(canvas, document):
    canvas.saveState()

    page_width, _ = A4

    if document.page > 1:
        canvas.setStrokeColor(colors.HexColor("#D9E2EC"))
        canvas.line(
            2 * cm,
            1.65 * cm,
            page_width - 2 * cm,
            1.65 * cm,
        )

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#526579"))

        canvas.drawString(
            2 * cm,
            1.15 * cm,
            "AI-Student-Insights | Exploratory Data Analysis",
        )

        canvas.drawRightString(
            page_width - 2 * cm,
            1.15 * cm,
            f"Page {document.page}",
        )

    canvas.restoreState()


document = SimpleDocTemplate(
    str(PDF_PATH),
    pagesize=A4,
    rightMargin=1.8 * cm,
    leftMargin=1.8 * cm,
    topMargin=1.9 * cm,
    bottomMargin=2.1 * cm,
    title="AI-Student-Insights: Exploratory Data Analysis",
    author="AI-Student-Insights Project",
    subject="Exploratory analysis of generative AI usage and student outcomes",
)


# ============================================================
# 9. HELPER FUNCTIONS
# ============================================================

story = []


def add_paragraph(text, style="BodyCustom"):
    story.append(Paragraph(text, styles[style]))


def add_heading(text):
    story.append(
        Paragraph(text, styles["SectionHeading"])
    )


def add_subheading(text):
    story.append(
        Paragraph(text, styles["SubHeadingCustom"])
    )


def add_bullet(text):
    add_paragraph(f"&bull; {text}")


def add_table(headers, data, widths=None):
    table_data = [
        [Paragraph(str(cell), styles["SmallCustom"]) for cell in headers]
    ]

    for row in data:
        table_data.append(
            [
                Paragraph(str(cell), styles["SmallCustom"])
                for cell in row
            ]
        )

    table = Table(
        table_data,
        colWidths=widths,
        repeatRows=1,
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#163A5F"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, -1),
                    colors.HexColor("#F4F7FA"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor("#D9E2EC"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 10))


def add_visualization(filename, caption, width=15.5 * cm):
    image_path = IMAGE_DIR / filename

    if not image_path.exists():
        add_paragraph(
            f"Visualization not found: {filename}",
            "SmallCustom",
        )
        return

    try:
        img = Image(str(image_path))

        scale = min(
            width / img.imageWidth,
            10.5 * cm / img.imageHeight,
        )

        img.drawWidth = img.imageWidth * scale
        img.drawHeight = img.imageHeight * scale
        img.hAlign = "CENTER"

        story.append(img)
        story.append(Spacer(1, 4))
        story.append(
            Paragraph(
                caption,
                styles["SmallCustom"],
            )
        )
        story.append(Spacer(1, 10))

    except Exception as exc:
        add_paragraph(
            f"Could not insert {filename}: {exc}",
            "SmallCustom",
        )


# ============================================================
# 10. COVER PAGE
# ============================================================

story.append(Spacer(1, 4.0 * cm))

story.append(
    Paragraph(
        "AI-STUDENT-INSIGHTS",
        styles["ReportTitle"],
    )
)

story.append(
    Paragraph(
        "Exploratory Data Analysis Report",
        styles["SubtitleCustom"],
    )
)

story.append(Spacer(1, 0.8 * cm))

story.append(
    Paragraph(
        "An exploratory study of generative AI usage, "
        "academic performance, study habits, exam anxiety, "
        "and student well-being.",
        styles["CoverDetails"],
    )
)

story.append(Spacer(1, 2.0 * cm))

story.append(
    Paragraph(
        f"Report generated: {date.today().strftime('%d %B %Y')}<br/>"
        f"Dataset records: {len(rows):,}<br/>"
        f"Dataset variables: {len(columns)}",
        styles["CoverDetails"],
    )
)

story.append(Spacer(1, 2.5 * cm))

story.append(
    Paragraph(
        "Prepared as a data analysis project using Python "
        "and exploratory statistical techniques.",
        styles["CoverDetails"],
    )
)

story.append(PageBreak())


# ============================================================
# 11. ABSTRACT
# ============================================================

add_heading("1. Abstract")

add_paragraph(
    "This project explores a dataset concerning generative "
    "artificial intelligence usage and student-related outcomes. "
    "The analysis examines usage patterns, academic performance, "
    "traditional study habits, perceived AI dependency, exam anxiety, "
    "skill retention, and burnout risk. The workflow includes "
    "dataset inspection, data-quality checks, descriptive statistics, "
    "distribution analysis, correlation analysis, and group-wise "
    "comparisons. Visualizations are used to identify patterns and "
    "relationships that may warrant further investigation. The findings "
    "are descriptive and do not establish that AI usage causes any "
    "particular academic or well-being outcome."
)


# ============================================================
# 12. INTRODUCTION AND PROBLEM STATEMENT
# ============================================================

add_heading("2. Introduction")

add_paragraph(
    "Generative AI tools are increasingly used for tasks such as "
    "debugging, drafting, summarizing, brainstorming, and answering "
    "questions. Understanding how these usage patterns relate to "
    "student outcomes can help identify trends worth investigating. "
    "Exploratory Data Analysis (EDA) provides a systematic way to "
    "inspect data, summarize variables, visualize distributions, "
    "and investigate relationships before building predictive models."
)

add_heading("3. Problem Statement")

add_paragraph(
    "The dataset contains multiple measures of AI usage, academic "
    "performance, study behavior, and student well-being. Without "
    "systematic analysis, it is difficult to understand how these "
    "variables are distributed and whether observable associations "
    "exist between them. This project addresses that need through "
    "structured exploratory analysis and data visualization."
)


# ============================================================
# 13. OBJECTIVES AND RESEARCH QUESTIONS
# ============================================================

add_heading("4. Objectives")

for objective in [
    "Inspect the structure and quality of the processed dataset.",
    "Summarize numerical variables using descriptive statistics.",
    "Examine categorical distributions and AI usage groups.",
    "Compare pre-semester and post-semester GPA values.",
    "Investigate relationships among AI usage, dependency, anxiety, "
    "study hours, and academic outcomes.",
    "Explore differences in skill retention and burnout risk across groups.",
    "Communicate findings through clear visualizations.",
]:
    add_bullet(objective)

add_heading("5. Research Questions")

for question in [
    "How are students distributed across AI usage groups?",
    "How do pre-semester and post-semester GPA values compare?",
    "Is weekly AI usage associated with perceived AI dependency?",
    "How does exam anxiety vary across AI usage groups?",
    "How do skill-retention scores differ across AI usage groups?",
    "How are AI usage hours distributed across burnout-risk categories?",
]:
    add_bullet(question)


# ============================================================
# 14. DATASET DESCRIPTION
# ============================================================

add_heading("6. Dataset Overview")

add_paragraph(
    f"The processed dataset contains {len(rows):,} records and "
    f"{len(columns)} columns. The analysis uses the processed CSV "
    "provided in the project's data/processed directory."
)

add_table(
    ["Dataset property", "Result"],
    [
        ["Number of records", f"{len(rows):,}"],
        ["Number of columns", str(len(columns))],
        ["Missing cells", f"{missing_cells:,}"],
        ["Duplicate rows", f"{duplicate_rows:,}"],
        [
            "Student_ID column",
            "Present" if "Student_ID" in columns else "Not present",
        ],
        [
            "Unused AI_Use_Group column",
            "Present" if "AI_Use_Group" in columns else "Not present",
        ],
    ],
    widths=[7 * cm, 8 * cm],
)

add_subheading("Variables Included")

for column in columns:
    add_bullet(column.replace("_", " "))


# ============================================================
# 15. DATA QUALITY
# ============================================================

add_heading("7. Data Quality Assessment")

add_paragraph(
    f"The script identified {missing_cells:,} empty or missing "
    f"cells and {duplicate_rows:,} duplicate rows in the processed "
    "dataset. These checks are based on the CSV currently loaded by "
    "this script. They do not independently prove that every value "
    "is valid, correctly labeled, or representative."
)

add_paragraph(
    "Additional checks should confirm numerical ranges, categorical "
    "labels, the derivation of AI_Usage_Group, and the provenance of "
    "the source data. The original Student_ID field should generally "
    "be excluded from statistical analysis when it functions only as "
    "an identifier."
)


# ============================================================
# 16. DESCRIPTIVE STATISTICS
# ============================================================

add_heading("8. Descriptive Statistics")

numeric_columns = [
    "Pre_Semester_GPA",
    "Weekly_GenAI_Hours",
    "Tool_Diversity",
    "Traditional_Study_Hours",
    "Perceived_AI_Dependency",
    "Anxiety_Level_During_Exams",
    "Post_Semester_GPA",
    "Skill_Retention_Score",
]

statistics_rows = []

for column in numeric_columns:
    if column not in columns:
        continue

    values = get_numeric_values(column)

    if not values:
        continue

    statistics_rows.append(
        [
            column.replace("_", " "),
            str(len(values)),
            format_number(statistics.mean(values)),
            format_number(statistics.median(values)),
            format_number(
                statistics.stdev(values)
                if len(values) > 1
                else None
            ),
            format_number(min(values)),
            format_number(max(values)),
        ]
    )

add_table(
    [
        "Variable",
        "N",
        "Mean",
        "Median",
        "Std. dev.",
        "Min",
        "Max",
    ],
    statistics_rows,
    widths=[
        4.0 * cm,
        1.0 * cm,
        1.6 * cm,
        1.6 * cm,
        1.6 * cm,
        1.4 * cm,
        1.4 * cm,
    ],
)

add_paragraph(
    "These statistics describe the values in the processed dataset. "
    "The standard deviation shown is the sample standard deviation."
)


# ============================================================
# 17. CATEGORICAL DISTRIBUTIONS
# ============================================================

add_heading("9. Categorical Analysis")

for column in [
    "Major_Category",
    "Year_of_Study",
    "Primary_Use_Case",
    "Prompt_Engineering_Skill",
    "Paid_Subscription",
    "Institutional_Policy",
    "Burnout_Risk_Level",
    "AI_Usage_Group",
]:
    if column not in columns:
        continue

    add_subheading(column.replace("_", " ") + " Distribution")

    counts = category_counts(column)

    add_table(
        ["Category", "Count", "Percentage"],
        [
            [
                category or "(blank)",
                f"{count:,}",
                f"{count / len(rows) * 100:.2f}%",
            ]
            for category, count in counts
        ],
        widths=[7 * cm, 3 * cm, 3 * cm],
    )


# ============================================================
# 18. ACADEMIC PERFORMANCE ANALYSIS
# ============================================================

add_heading("10. Academic Performance Analysis")

add_paragraph(
    f"The mean pre-semester GPA is "
    f"{format_number(mean_value('Pre_Semester_GPA'))}, while the "
    f"mean post-semester GPA is "
    f"{format_number(mean_value('Post_Semester_GPA'))}."
)

add_paragraph(
    f"The mean paired GPA change is "
    f"{format_number(mean_gpa_change)} points, calculated as "
    "post-semester GPA minus pre-semester GPA for rows with valid "
    "values in both columns."
)

add_table(
    ["GPA change category", "Count", "Percentage"],
    [
        [
            "Improved",
            f"{improved:,}",
            f"{gpa_improved_pct:.2f}%",
        ],
        [
            "Unchanged",
            f"{unchanged:,}",
            f"{gpa_unchanged_pct:.2f}%",
        ],
        [
            "Declined",
            f"{declined:,}",
            f"{gpa_declined_pct:.2f}%",
        ],
    ],
    widths=[6 * cm, 3 * cm, 3 * cm],
)

add_paragraph(
    "A change in GPA between two measurements does not establish "
    "that AI usage caused the change. The report also does not "
    "assume that the GPA scale or measurement process is valid "
    "without verification from the dataset documentation."
)

add_visualization(
    "pre_semester_gpa_distribution.png",
    "Figure 1. Distribution of pre-semester GPA.",
)

add_visualization(
    "post_semester_gpa_distribution.png",
    "Figure 2. Distribution of post-semester GPA.",
)

add_visualization(
    "gpa_change_distribution.png",
    "Figure 3. Distribution of changes between the two GPA measurements.",
)

add_visualization(
    "post_semester_gpa_by_prompt_engineering_skill.png",
    "Figure 4. Post-semester GPA by prompt-engineering skill level.",
)


# ============================================================
# 19. AI USAGE AND STUDENT WELL-BEING
# ============================================================

add_heading("11. AI Usage and Student Well-Being")

add_paragraph(
    "This section examines AI usage alongside perceived AI dependency, "
    "exam anxiety, traditional study hours, and burnout-risk categories. "
    "Group comparisons describe differences in the observed data and "
    "should not be interpreted as causal effects."
)

add_visualization(
    "weekly_genai_hours_distribution.png",
    "Figure 5. Distribution of weekly generative AI usage hours.",
)

add_visualization(
    "perceived_ai_dependency_distribution.png",
    "Figure 6. Distribution of perceived AI dependency.",
)

add_visualization(
    "anxiety_during_exams_distribution.png",
    "Figure 7. Distribution of exam anxiety levels.",
)

add_visualization(
    "anxiety_levels_by_ai_usage.png",
    "Figure 8. Exam anxiety across AI usage groups.",
)

add_visualization(
    "weekly_genai_hours_by_burnout_risk.png",
    "Figure 9. Weekly AI usage hours across burnout-risk categories.",
)

add_visualization(
    "weekly_genai_vs_perceived_ai_dependency.png",
    "Figure 10. Relationship between AI usage hours and perceived dependency.",
)

add_visualization(
    "weekly_genai_vs_traditional_study.png",
    "Figure 11. Relationship between AI usage and traditional study hours.",
)


# ============================================================
# 20. SKILL RETENTION
# ============================================================

add_heading("12. Skill Retention Analysis")

add_paragraph(
    "Skill retention is examined across AI usage groups to identify "
    "differences in the distribution and typical values of the recorded "
    "scores. These comparisons do not establish whether AI usage "
    "improves or reduces skill retention."
)

add_visualization(
    "skill_retention_scores_distribution.png",
    "Figure 12. Distribution of skill-retention scores.",
)

add_visualization(
    "skill_retention_by_ai_usage.png",
    "Figure 13. Skill-retention scores across AI usage groups.",
)


# ============================================================
# 21. CORRELATION ANALYSIS
# ============================================================

add_heading("13. Correlation Analysis")

correlation_rows = []

for column_x, column_y, label in correlation_pairs:
    if column_x not in columns or column_y not in columns:
        continue

    coefficient = pearson_correlation(column_x, column_y)

    correlation_rows.append(
        [
            label,
            format_number(coefficient, 3),
        ]
    )

add_table(
    ["Variable pair", "Pearson r"],
    correlation_rows,
    widths=[10 * cm, 3 * cm],
)

add_paragraph(
    "Pearson's correlation coefficient measures the strength and "
    "direction of a linear association. A positive coefficient "
    "indicates that the variables tend to increase together; a "
    "negative coefficient indicates an inverse linear association. "
    "A coefficient near zero indicates little linear association, "
    "but does not rule out nonlinear relationships."
)

add_paragraph(
    "Correlation does not imply causation. These exploratory "
    "coefficients do not, by themselves, establish statistical "
    "significance or control for confounding variables."
)

add_visualization(
    "correlation_heatmap.png",
    "Figure 14. Correlation heatmap for numerical variables.",
)


# ============================================================
# 22. REMAINING VISUALIZATIONS
# ============================================================

add_heading("14. Additional Visualizations")

additional_visualizations = [
    (
        "major_category_distribution.png",
        "Distribution of students across major categories.",
    ),
    (
        "year_of_study_distribution.png",
        "Distribution of students by year of study.",
    ),
    (
        "primary_use_case_distribution.png",
        "Distribution of primary generative AI use cases.",
    ),
    (
        "prompt_engineering_skill_distribution.png",
        "Distribution of prompt-engineering skill levels.",
    ),
    (
        "paid_subscription_distribution.png",
        "Distribution of paid subscription status.",
    ),
    (
        "institutional_policy_distribution.png",
        "Distribution of institutional AI policies.",
    ),
    (
        "burnout_risk_level_distribution.png",
        "Distribution of burnout-risk categories.",
    ),
    (
        "weekly_traditional_study_hours_distribution.png",
        "Distribution of traditional study hours.",
    ),
]

for filename, caption in additional_visualizations:
    add_visualization(filename, caption)


# ============================================================
# 23. KEY FINDINGS
# ============================================================

add_heading("15. Key Findings")

add_paragraph(
    f"The processed dataset contains {len(rows):,} records. "
    f"The average pre-semester GPA is "
    f"{format_number(mean_value('Pre_Semester_GPA'))}, compared with "
    f"{format_number(mean_value('Post_Semester_GPA'))} for "
    "post-semester GPA."
)

if gpa_differences:
    add_paragraph(
        f"Among {paired_count:,} records with valid paired GPA values, "
        f"{improved:,} ({gpa_improved_pct:.2f}%) show an increase, "
        f"{unchanged:,} ({gpa_unchanged_pct:.2f}%) are unchanged, and "
        f"{declined:,} ({gpa_declined_pct:.2f}%) show a decrease."
    )

if ai_group_counts:
    add_paragraph(
        "The AI usage group counts are: "
        + "; ".join(
            f"{category}: {count:,} "
            f"({count / len(rows) * 100:.2f}%)"
            for category, count in ai_group_counts
        )
        + "."
    )

r_ai_dependency = pearson_correlation(
    "Weekly_GenAI_Hours",
    "Perceived_AI_Dependency",
)

if r_ai_dependency is not None:
    add_paragraph(
        "The Pearson correlation between weekly AI usage and perceived "
        f"AI dependency is {r_ai_dependency:.3f}. This describes a "
        "linear association in the dataset and does not establish causality."
    )

r_ai_anxiety = pearson_correlation(
    "Weekly_GenAI_Hours",
    "Anxiety_Level_During_Exams",
)

if r_ai_anxiety is not None:
    add_paragraph(
        "The Pearson correlation between weekly AI usage and exam "
        f"anxiety is {r_ai_anxiety:.3f}. This result should be "
        "interpreted alongside the variable definitions, data quality, "
        "and possible confounding factors."
    )

add_paragraph(
    "The visualizations and group comparisons provide a descriptive "
    "overview of AI usage patterns, academic measures, and student "
    "well-being indicators. Findings should be verified against the "
    "dataset documentation before making broader claims."
)


# ============================================================
# 24. LIMITATIONS
# ============================================================

add_heading("16. Limitations")

for limitation in [
    "The representativeness of the dataset cannot be established "
    "without documentation of its source and sampling method.",
    "Associations observed in this analysis do not establish causation.",
    "Potential confounding factors may affect academic performance, "
    "study habits, anxiety, and burnout risk.",
    "Pearson correlation captures linear associations and may not "
    "fully describe nonlinear relationships.",
    "The definitions and measurement methods for GPA, dependency, "
    "anxiety, skill retention, and burnout risk should be verified.",
    "The method used to derive AI_Usage_Group should be documented "
    "and checked against the raw weekly AI usage values.",
    "No predictive model or causal inference analysis is performed "
    "in this report.",
]:
    add_bullet(limitation)


# ============================================================
# 25. CONCLUSION
# ============================================================

add_heading("17. Conclusion")

add_paragraph(
    "This project applies Exploratory Data Analysis to investigate "
    "patterns in generative AI usage and student-related outcomes. "
    "It combines data-quality checks, descriptive statistics, "
    "categorical summaries, GPA comparisons, correlation analysis, "
    "and visualizations to provide an overview of the processed data."
)

add_paragraph(
    "The analysis provides a foundation for more detailed work, "
    "including hypothesis testing, subgroup comparisons, regression "
    "analysis, and predictive modeling. Any further analysis should "
    "begin by verifying the source, definitions, and reliability of "
    "the dataset. Conclusions should remain proportional to the "
    "evidence and should not treat observational associations as "
    "proof of cause and effect."
)


# ============================================================
# 26. METHODOLOGY AND REPRODUCIBILITY
# ============================================================

add_heading("18. Tools and Methodology")

add_table(
    ["Component", "Purpose"],
    [
        ["Python", "Data processing and analysis"],
        ["CSV module", "Loading the processed dataset"],
        ["statistics", "Descriptive statistics"],
        ["ReportLab", "PDF report generation"],
        ["Matplotlib / Seaborn", "Source of exported visualizations"],
        ["Jupyter Notebook", "Interactive EDA workflow"],
    ],
    widths=[5 * cm, 9 * cm],
)

add_paragraph(
    "This PDF is generated from the processed CSV and PNG files "
    "available in the project directory. The report generator "
    "recalculates its numerical summaries from the CSV at runtime. "
    "It does not independently rerun the notebook's preprocessing "
    "or regenerate the exported charts."
)

add_paragraph(
    "For reproducibility, retain the raw dataset, processed dataset, "
    "notebook, requirements file, visualization files, and this "
    "report-generation script together in the project repository."
)


# ============================================================
# 27. GENERATE PDF
# ============================================================

document.build(
    story,
    onFirstPage=add_page_number,
    onLaterPages=add_page_number,
)

print("\n" + "=" * 60)
print("REPORT GENERATED SUCCESSFULLY")
print("=" * 60)
print(f"PDF location: {PDF_PATH}")
print(f"File exists: {PDF_PATH.exists()}")

if PDF_PATH.exists():
    print(f"File size: {PDF_PATH.stat().st_size / 1024:.2f} KB")

print("\nPlease open the PDF and review its content and formatting.")