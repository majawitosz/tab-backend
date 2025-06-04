import io
from datetime import datetime, date
from typing import Literal

import matplotlib.pyplot as plt
from django.core.files.base import ContentFile
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import TruncDate
from ninja import Schema
from ninja_extra import NinjaExtraAPI
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)

from .models import Report
from apps.dania.models import Order, OrderItem

api = NinjaExtraAPI(version="1.0", urls_namespace="reports")


class ReportGenerateInput(Schema):
    start_date: date
    end_date: date
    filter_by: Literal['overall_income', 'dish_popularity', 'dish_income']


class FileUrlSchema(Schema):
    file_url: str


@api.post("/generate", response=FileUrlSchema)
def generate_report(request, data: ReportGenerateInput):
    # 1) Pobranie i przygotowanie danych
    title_map = {
        'overall_income': ("Przychód dzienny", "Data", "Przychód [PLN]"),
        'dish_popularity': ("Popularność dań", "Danie", "Ilość zamówień"),
        'dish_income': ("Dochód po daniu", "Danie", "Przychód [PLN]"),
    }
    title, col1, col2 = title_map[data.filter_by]

    if data.filter_by == 'overall_income':
        qs = (
            Order.objects
            .filter(created_at__date__gte=data.start_date, created_at__date__lte=data.end_date)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(value=Sum('total_amount'))
            .order_by('day')
        )
        rows = [(e['day'].strftime('%Y-%m-%d'), float(e['value'])) for e in qs]

    else:
        field = 'count' if data.filter_by == 'dish_popularity' else 'income'
        agg = Sum('quantity') if data.filter_by == 'dish_popularity' else Sum(
            F('quantity') * F('price_at_time'), output_field=DecimalField())
        qs = (
            OrderItem.objects
            .filter(order__created_at__date__gte=data.start_date, order__created_at__date__lte=data.end_date)
            .values('menu_item__name')
            .annotate(value=agg)
            .order_by('-value')[:10]
        )
        rows = [(e['menu_item__name'], float(e['value'])) for e in qs]

    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]

    # 2) Generacja wykresu
    fig, ax = plt.subplots(figsize=(6, 4))
    if data.filter_by == 'overall_income':
        ax.plot(labels, values, marker='o', color='navy')
    else:
        ax.barh(labels, values, color='teal')
        ax.invert_yaxis()
    ax.set_title(title)
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    plt.xticks(rotation=45, ha='right')
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format='PNG')
    plt.close(fig)
    buf.seek(0)

    # 3) Budowa PDF przez Platypus
    pdf_buf = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buf, pagesize=A4,
                            leftMargin=30, rightMargin=30,
                            topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elems = []

    # Tytuł
    elems.append(Paragraph(f"Raport: {title}", styles['Heading1']))
    elems.append(Spacer(1, 12))

    # Podsumowanie parametrów
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary_data = [
        ["Okres", f"{data.start_date} – {data.end_date}"],
        ["Typ raportu", title],
        ["Wygenerowano", now],
    ]
    tbl_sum = Table(summary_data, colWidths=[100, 300])
    tbl_sum.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elems.extend([tbl_sum, Spacer(1, 24)])

    # Tabelka z wynikami
    table_data = [[col1, col2]] + [[r[0], f"{r[1]:,.2f}"] for r in rows]
    tbl = Table(table_data, colWidths=[250, 150])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d3d3d3')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elems.extend([tbl, Spacer(1, 24)])

    # Wstawiamy wykres
    img = Image(buf, width=450, height=300)
    elems.append(img)

    doc.build(elems)
    pdf_buf.seek(0)

    # 4) Zapis do modelu i zwrot URL
    fname = f"{data.filter_by}_{datetime.now():%Y%m%d%H%M%S}.pdf"
    report = Report(
        title=fname,
        start_date=data.start_date,
        end_date=data.end_date,
        filter_by=data.filter_by,
        data={"rows": rows}
    )
    report.file.save(fname, ContentFile(pdf_buf.read()))
    report.save()

    return {"file_url": request.build_absolute_uri(report.file.url)}