import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


DEFAULT_OUTPUT = Path('output/pdf/yatube_app_summary_one_pager.pdf')


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate a one-page PDF summary for the Yatube app.'
    )
    parser.add_argument(
        '--out',
        default=str(DEFAULT_OUTPUT),
        help='Output PDF path (default: output/pdf/yatube_app_summary_one_pager.pdf)',
    )
    return parser.parse_args()


def build_pdf(output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='TitleCustom',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=21,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name='HeadingCustom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=13,
        textColor=colors.HexColor('#133a63'),
        spaceBefore=5,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name='BodyCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        leading=11.5,
        textColor=colors.HexColor('#111111'),
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name='SmallCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#444444'),
    ))

    story = []
    story.append(Paragraph('Yatube App Summary', styles['TitleCustom']))
    story.append(Paragraph('Repository-based one-page brief', styles['SmallCustom']))
    story.append(Spacer(1, 4))

    story.append(Paragraph('What it is', styles['HeadingCustom']))
    story.append(Paragraph(
        'Yatube is a Django web app described in the repo as a social network for bloggers. '
        'It provides server-rendered pages for publishing posts, following authors, and interacting through comments and profiles.',
        styles['BodyCustom']
    ))

    story.append(Paragraph('Who it\'s for', styles['HeadingCustom']))
    story.append(Paragraph(
        'Primary persona: bloggers and readers who want a lightweight, feed-based community experience with profiles and subscriptions.',
        styles['BodyCustom']
    ))

    story.append(Paragraph('What it does', styles['HeadingCustom']))
    feature_items = [
        'Shows a global post feed with pagination (10 posts per page).',
        'Supports group-specific feeds by group slug.',
        'Provides user profile pages with authored posts and follow status.',
        'Lets authenticated users create, edit, and delete posts, including optional images.',
        'Lets authenticated users add comments on post detail pages.',
        'Supports follow and unfollow actions plus a personalized follow feed.',
        'Includes sign up, login, logout, and profile editing (bio and avatar).',
    ]
    story.append(ListFlowable(
        [ListItem(Paragraph(item, styles['BodyCustom']), leftIndent=0) for item in feature_items],
        bulletType='bullet',
        start='circle',
        leftIndent=12,
        bulletFontName='Helvetica',
        bulletFontSize=7,
        bulletOffsetY=1,
        spaceBefore=1,
        spaceAfter=1,
    ))

    story.append(Paragraph('How it works (repo evidence)', styles['HeadingCustom']))
    arch_items = [
        'Structure: Django monolith split into apps `posts`, `users`, and `core` (custom 403/404/500 handlers).',
        'Request path: browser request -> `yatube/urls.py` router -> app views -> templates in `yatube/templates/*`.',
        'Business/data layer: models `Post`, `Group`, `Comment`, `Follow`, `Profile`, and Django `User`; ORM queries with pagination and auth checks.',
        'Storage: SQLite by default for local runs; `DATABASE_URL` enables PostgreSQL in deployment configs.',
        'Assets/runtime: uploaded media in `MEDIA_ROOT`; static files served with WhiteNoise; WSGI app served by Gunicorn in `Procfile`/`render.yaml`.',
        'Caching: local in-memory cache backend (`LocMemCache`) configured in settings.',
    ]
    story.append(ListFlowable(
        [ListItem(Paragraph(item, styles['BodyCustom']), leftIndent=0) for item in arch_items],
        bulletType='bullet',
        start='circle',
        leftIndent=12,
        bulletFontName='Helvetica',
        bulletFontSize=7,
        bulletOffsetY=1,
        spaceBefore=1,
        spaceAfter=1,
    ))

    story.append(Paragraph('How to run (minimal)', styles['HeadingCustom']))
    run_items = [
        'Install dependencies: `pip install -r requirements.txt`.',
        'Set environment: copy `.env.example` to `.env` and set at least `DJANGO_SECRET_KEY` (required by settings).',
        'Apply DB migrations: `cd yatube && python manage.py migrate`.',
        'Optional static build step used in deploy script: `python manage.py collectstatic --no-input`.',
        'Start app using repo-defined process: `gunicorn yatube.wsgi` from `yatube/` directory.',
        'Local `python manage.py runserver` command: Not found in repo.',
    ]
    story.append(ListFlowable(
        [ListItem(Paragraph(item, styles['BodyCustom']), leftIndent=0) for item in run_items],
        bulletType='bullet',
        start='circle',
        leftIndent=12,
        bulletFontName='Helvetica',
        bulletFontSize=7,
        bulletOffsetY=1,
        spaceBefore=1,
        spaceAfter=1,
    ))

    story.append(Spacer(1, 3))
    story.append(Paragraph(
        'Notes: Any missing operational details are explicitly labeled as Not found in repo.',
        styles['SmallCustom']
    ))

    doc.build(story)
    print(output_path)


def main():
    args = parse_args()
    build_pdf(args.out)


if __name__ == '__main__':
    main()
