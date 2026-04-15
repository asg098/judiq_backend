import os
import logging
from datetime import datetime
from io import BytesIO
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PDFGenerator:
    @staticmethod
    def generate_report(analysis_result: Dict[str, Any]) -> bytes:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, 
                                   rightMargin=72, leftMargin=72,
                                   topMargin=72, bottomMargin=18)
            elements = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle', parent=styles['Heading1'], fontSize=24, 
                textColor=colors.HexColor('#1a1a1a'), spaceAfter=30, alignment=TA_CENTER
            )
            heading_style = ParagraphStyle(
                'CustomHeading', parent=styles['Heading2'], fontSize=16,
                textColor=colors.HexColor('#2c3e50'), spaceAfter=12, spaceBefore=12
            )
            elements.append(Paragraph("JudiQ Legal Case Intelligence Report", title_style))
            elements.append(Spacer(1, 0.2*inch))
            score = analysis_result.get('score', 0)
            summary_data = [
                ['Case Score:', f"{score}/100"],
                ['Verdict:', analysis_result.get('verdict', 'Unknown')],
                ['Report Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            ]
            summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('PADDING', (0, 0), (-1, -1), 10)
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("Scoring Logic & Evidence Trace", heading_style))
            for trace in analysis_result.get('scoring_trace', []):
                elements.append(Paragraph(f"• {trace}", styles['Normal']))
                elements.append(Spacer(1, 0.05*inch))
            elements.append(Paragraph("Legal Defence Simulation", heading_style))
            defences = analysis_result.get('defences', [])
            if defences:
                for d in defences:
                    elements.append(Paragraph(f"<b>{d['argument']}</b>", styles['Normal']))
                    elements.append(Paragraph(f"Probability: {d['success_probability']}% | Strength: {d['strength']}", styles['Italic']))
                    elements.append(Paragraph(f"Counter: {d['rebuttal']}", styles['Normal']))
                    elements.append(Spacer(1, 0.1*inch))
            doc.build(elements)
            return buffer.getvalue()
        except ImportError:
            logger.warning("ReportLab not found. Returning text-based dump.")
            return str(analysis_result).encode('utf-8')
        except Exception as e:
            logger.error(f"PDF Gen Error: {e}")
            return b""
