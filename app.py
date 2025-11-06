def generuj_pdf_reportlab(df_sorted, nazwa_zawodow=""):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # --- Nagłówek z nazwą zawodów ---
    if nazwa_zawodow:
        elements.append(Paragraph(f"🏆 {nazwa_zawodow}", styles['Heading1']))
        elements.append(Spacer(1, 15))

    # --- Ranking ogólny ---
    elements.append(Paragraph("📊 Ranking końcowy (wszyscy zawodnicy)", styles['Heading2']))
    elements.append(Spacer(1, 10))
    data = [["Miejsce", "Imię", "Sektor", "Stanowisko", "Waga", "Miejsce w sektorze"]]
    for _, row in df_sorted.iterrows():
        data.append([
            int(row['miejsce_ogolne']),
            row['imie'],
            row['sektor'],
            row['stanowisko'],
            row['waga'],
            int(row['miejsce_w_sektorze'])
        ])
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ]))
    # Naprzemienne kolorowanie wierszy + wyróżnienie zwycięzcy
    for i in range(1, len(data)):
        if i % 2 == 0:
            t.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), colors.lightgrey)]))
        if i == 1:  # zwycięzca (miejsce 1)
            t.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), colors.lightgreen),
                                   ('FONTNAME', (0,i), (-1,i), 'Helvetica-Bold')]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # --- Podsumowanie sektorów z miejscem ogólnym ---
    elements.append(Paragraph("📌 Podsumowanie sektorów", styles['Heading2']))
    elements.append(Spacer(1, 10))
    for sektor, grupa in df_sorted.groupby("sektor"):
        elements.append(Paragraph(f"Sektor {sektor}", styles['Heading3']))
        data = [["Imię", "Stanowisko", "Waga", "Miejsce w sektorze", "Miejsce ogólne"]]
        for _, row in grupa.sort_values(by="waga", ascending=False).iterrows():
            data.append([
                row['imie'],
                row['stanowisko'],
                row['waga'],
                int(row['miejsce_w_sektorze']),
                int(row['miejsce_ogolne'])
            ])
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ]))
        # Naprzemienne kolorowanie + wyróżnienie zwycięzcy w sektorze
        for i in range(1, len(data)):
            if i % 2 == 0:
                t.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), colors.lightgrey)]))
            if i == 1:  # zwycięzca sektora
                t.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), colors.lightgreen),
                                       ('FONTNAME', (0,i), (-1,i), 'Helvetica-Bold')]))
        elements.append(t)
        elements.append(Spacer(1, 15))

    doc.build(elements)
    buffer.seek(0)
    return buffer
