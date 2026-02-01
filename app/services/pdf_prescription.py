import os
from io import BytesIO
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    TableStyle,
    Spacer,
    Image,
)


def _doctor_display_name(doctor, doctor_profile=None) -> str:
    if doctor_profile and doctor_profile.full_name:
        return doctor_profile.full_name
    if getattr(doctor, "full_name", None):
        return doctor.full_name
    first = getattr(doctor, "first_name", "") or ""
    last = getattr(doctor, "last_name", "") or ""
    if first or last:
        return f"{first} {last}".strip() or "Médico"
    return f"Dr. {doctor.email}" if getattr(doctor, "email", None) else "Médico"


def _doctor_field(doctor_profile, doctor, profile_attr: str, user_attr: str = "email") -> str:
    if doctor_profile and getattr(doctor_profile, profile_attr, None):
        return getattr(doctor_profile, profile_attr) or "-"
    return getattr(doctor, user_attr, None) or "-"


def _patient_age(date_of_birth) -> str | None:
    if not date_of_birth:
        return None
    today = date.today()
    age = (
        today.year
        - date_of_birth.year
        - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    )
    return str(age) if age >= 0 else None


def _safe_image(path: str | None, max_width_cm: float = 4, max_height_cm: float = 2):
    if not path or not path.strip():
        return None
    path = path.strip()
    if not os.path.isfile(path):
        return None
    try:
        img = Image(path)
        w, h = img.imageWidth, img.imageHeight
        if w <= 0 or h <= 0:
            return None
        scale = min((max_width_cm * cm) / w, (max_height_cm * cm) / h, 1.0)
        img.drawWidth = w * scale
        img.drawHeight = h * scale
        return img
    except Exception:
        return None


def generate_prescription_pdf(prescription, doctor, patient, doctor_profile=None) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="CustomTitle",
        parent=styles["Heading1"],
        fontSize=15,
        fontName="Helvetica-Bold",
        spaceAfter=6,
    )
    normal_style = ParagraphStyle(
        name="Body",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=12,
    )
    section_style = ParagraphStyle(
        name="SectionTitle",
        parent=styles["Heading2"],
        fontSize=10.5,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#2F3B52"),
        spaceBefore=8,
        spaceAfter=4,
    )
    muted_style = ParagraphStyle(
        name="Muted",
        parent=styles["Normal"],
        textColor=colors.HexColor("#6B7280"),
        fontSize=8.5,
    )

    # ---- HEADER ----
    doctor_name = _doctor_display_name(doctor, doctor_profile)
    city = "-"
    if doctor_profile and getattr(doctor_profile, "ciudad", None):
        city = doctor_profile.ciudad or "-"
    prescription_date = prescription.created_at
    emission_str = prescription_date.strftime("%d/%m/%Y") if prescription_date else "-"
    story = [
        Paragraph("RECETA MÉDICA", title_style),
        Paragraph(
            f"Ciudad: {city} · Fecha de emisión: {emission_str}",
            muted_style,
        ),
        Spacer(1, 0.35 * cm),
        Table(
            [[" "]],
            colWidths=[17 * cm],
            rowHeights=[0.1 * cm],
            style=TableStyle([
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ]),
        ),
        Spacer(1, 0.35 * cm),
        Paragraph("Datos del médico", section_style),
        Paragraph(f"Nombre: {doctor_name}", normal_style),
        Paragraph(
            f"Especialidad: {_doctor_field(doctor_profile, doctor, 'specialty')}",
            normal_style,
        ),
        Paragraph(
            f"Registro profesional (SENESCYT / MSP): {_doctor_field(doctor_profile, doctor, 'senescyt_reg')}",
            normal_style,
        ),
        Paragraph(
            f"Nº de licencia médica: {_doctor_field(doctor_profile, doctor, 'medical_license')}",
            normal_style,
        ),
        Paragraph(
            f"Teléfono / Email: {_doctor_field(doctor_profile, doctor, 'phone')} · {_doctor_field(doctor_profile, doctor, 'email', 'email')}",
            normal_style,
        ),
        Paragraph(
            f"Dirección: {_doctor_field(doctor_profile, doctor, 'address')}",
            normal_style,
        ),
        Spacer(1, 0.4 * cm),
    ]

    # ---- PATIENT INFO ----
    patient_full = f"{patient.first_name} {patient.last_name}"
    age_str = _patient_age(patient.date_of_birth)
    story.extend([
        Paragraph("Datos del paciente", section_style),
        Paragraph(f"Nombre completo: {patient_full}", normal_style),
        Paragraph(
            f"Edad: {age_str if age_str else '-'} años",
            normal_style,
        ),
        Paragraph(f"Fecha de atención: {emission_str}", normal_style),
        Spacer(1, 0.4 * cm),
    ])

    # ---- DIAGNOSIS ----
    diagnosis_code = None
    diagnosis_desc = None
    diagnosis_text = None
    if getattr(prescription, "consultation", None):
        diagnosis_code = getattr(prescription.consultation, "diagnosis_code", None)
        diagnosis_desc = getattr(prescription.consultation, "diagnosis_description", None)
        diagnosis_text = getattr(prescription.consultation, "diagnosis", None)
    story.append(Paragraph("Diagnóstico", section_style))
    if diagnosis_code or diagnosis_desc:
        code = diagnosis_code or "-"
        desc = diagnosis_desc or "-"
        story.append(Paragraph(f"CIE-10: {code} — {desc}", normal_style))
    elif diagnosis_text:
        story.append(Paragraph(f"Diagnóstico clínico: {diagnosis_text}", normal_style))
    else:
        story.append(Paragraph("Diagnóstico clínico: —", muted_style))
    story.append(Spacer(1, 0.4 * cm))

    # ---- PRESCRIPTION TABLE ----
    story.append(Paragraph("Prescripción", section_style))
    cols = [
        "Medicamento",
        "Dosis",
        "Frecuencia",
        "Duración",
        "Vía",
        "Cantidad",
        "Observaciones",
    ]
    data = [cols]
    for item in prescription.items:
        data.append([
            Paragraph(f"<b>{item.medication_name or '-'}</b>", normal_style),
            item.dose or "-",
            item.frequency or "-",
            item.duration or "-",
            item.route or "-",
            item.quantity or "-",
            item.notes or "-",
        ])
    col_widths = [4.0 * cm, 2.1 * cm, 2.3 * cm, 2.2 * cm, 1.7 * cm, 1.7 * cm, 3.0 * cm]
    t = Table(data, colWidths=col_widths)
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("ALIGN", (4, 1), (4, -1), "CENTER"),
            ("ALIGN", (5, 1), (5, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
        ])
    )
    story.extend([t, Spacer(1, 0.4 * cm)])

    # ---- GENERAL INSTRUCTIONS ----
    story.append(Paragraph("Indicaciones generales", section_style))
    story.append(Paragraph(prescription.general_instructions or "—", normal_style))
    story.append(Spacer(1, 0.4 * cm))

    # ---- SIGNATURE AREA (images: prefer signature_url/stamp_url, then signature_image/stamp_image) ----
    story.append(Spacer(1, 0.6 * cm))
    sig_img = None
    stamp_img = None
    if doctor_profile:
        sig_path = getattr(doctor_profile, "signature_url", None) or getattr(
            doctor_profile, "signature_image", None
        )
        if sig_path:
            sig_img = _safe_image(sig_path, max_width_cm=5.5, max_height_cm=4.2)
        stamp_path = getattr(doctor_profile, "stamp_url", None) or getattr(
            doctor_profile, "stamp_image", None
        )
        if stamp_path:
            stamp_img = _safe_image(stamp_path, max_width_cm=4.5, max_height_cm=3.5)
    if sig_img:
        story.append(sig_img)
    if stamp_img:
        story.append(Spacer(1, 0.2 * cm))
        story.append(stamp_img)
    story.append(
        Paragraph(
            "Firma y sello del médico",
            ParagraphStyle(
                name="Signature",
                parent=normal_style,
                fontSize=10,
                alignment=1,
                spaceBefore=12,
            ),
        )
    )
    story.append(Paragraph(
        doctor_name,
        ParagraphStyle(
            name="DoctorName",
            parent=normal_style,
            fontSize=9,
            alignment=1,
            textColor=colors.HexColor("#374151"),
        ),
    ))
    story.append(Spacer(1, 0.4 * cm))

    # ---- FOOTER ----
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(
        Paragraph(
            f"<i>Documento médico generado digitalmente</i> · {generated_at}",
            ParagraphStyle(
                name="Footer",
                parent=normal_style,
                fontSize=8,
                alignment=2,
                textColor=colors.grey,
            ),
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer
