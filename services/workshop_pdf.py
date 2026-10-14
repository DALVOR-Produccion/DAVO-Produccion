"""PDF imprimible a partir de una sola ficha del banco existente."""
from html.parser import HTMLParser
from html import escape
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []


class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root=Node();self.stack=[self.root]
    def handle_starttag(self, tag, attrs):
        node=Node(tag,attrs);self.stack[-1].children.append(node)
        if tag not in ('br','hr','img','input','meta','link'):self.stack.append(node)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:
                self.stack=self.stack[:i];break
    def handle_data(self, data):self.stack[-1].children.append(data)


def normalize(text):
    return text.replace('\u2011','-').replace('\u2013','-').replace('\u2014','-').replace('\u202f',' ')


def inline(node):
    if isinstance(node,str):return escape(normalize(node))
    body=''.join(inline(c) for c in node.children)
    if node.tag in ('b','strong'):return '<b>'+body+'</b>'
    if node.tag in ('i','em'):return '<i>'+body+'</i>'
    if node.tag=='br':return '<br/>'
    if node.tag=='p':return body+'<br/>'
    if node.tag=='a':
        href=node.attrs.get('href','')
        return '<a href="'+escape(href,quote=True)+'" color="#123c75">'+body+'</a>' if href.startswith('https://') else body
    return body


def plain(node):
    return node if isinstance(node,str) else ''.join(plain(c) for c in node.children)


def create_workshop_pdf(item, intro, school_name, course, section, enrollment):
    stream=BytesIO()
    styles=getSampleStyleSheet()
    normal=ParagraphStyle('WorkshopBody',parent=styles['Normal'],fontName='Helvetica',fontSize=10,leading=14,spaceAfter=8)
    heading=ParagraphStyle('WorkshopHeading',parent=styles['Heading2'],fontName='Helvetica-Bold',fontSize=14,leading=18,textColor=colors.HexColor('#123c75'),spaceBefore=12,spaceAfter=9,keepWithNext=True)
    title=ParagraphStyle('WorkshopTitle',parent=heading,fontSize=22,leading=27,spaceBefore=0)
    cell=ParagraphStyle('WorkshopCell',parent=normal,fontSize=9,leading=12,spaceAfter=0)
    small=ParagraphStyle('WorkshopSmall',parent=normal,fontSize=9,leading=12,textColor=colors.HexColor('#475467'))
    width=A4[0]-88
    story=[Paragraph('SIOE · Material del taller',small),Paragraph(escape(item['name']),title),
        Paragraph(escape(f'{school_name} · {course} {section}'),normal),
        Paragraph(f"Ficha {escape(item['id'])} · {enrollment.sessions} sesiones · Seleccionado el {enrollment.started_on.strftime('%d-%m-%Y')}",small),
        Paragraph('Material para uso educativo interno del establecimiento. Propuesta para revisión y pilotaje; no se afirma validación externa.',small)]

    def table(node):
        rows=[c for c in node.children if isinstance(c,Node) and c.tag=='tr']
        if not rows:
            rows=[r for container in node.children if isinstance(container,Node) for r in container.children if isinstance(r,Node) and r.tag=='tr']
        if not rows:return
        raw=[[c for c in r.children if isinstance(c,Node) and c.tag in ('td','th')] for r in rows]
        count=max(len(r) for r in raw)
        header_text=' '.join(plain(c) for c in raw[0])
        if count==4 and 'Sesión' in header_text:fractions=[.10,.23,.44,.23]
        elif count==3:fractions=[.33,.34,.33]
        else:fractions=[1/count]*count
        data=[];heights=[]
        for r in raw:
            data.append([Paragraph(inline(c).strip() or ' ',cell) for c in r]+['']*(count-len(r)))
            # Preserve blank writing space without fixed heights for text-heavy rows.
            height=78 if any('100px' in c.attrs.get('style','') for c in r) else (44 if any('45px' in c.attrs.get('style','') for c in r) else None)
            heights.append(height)
        has_header=all(c.tag=='th' for c in raw[0])
        result=Table(data,colWidths=[width*f for f in fractions],rowHeights=heights,repeatRows=1 if has_header else 0,hAlign='LEFT')
        commands=[('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#b9c8d5')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]
        if has_header:commands.append(('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9f0f6')))
        result.setStyle(TableStyle(commands));story.extend([result,Spacer(1,12)])

    def visit(node):
        if isinstance(node,str):return
        if node.tag in ('script','style','nav'):return
        if node.tag=='article':story.append(PageBreak())
        if node.tag=='section' and 'hoja' in node.attrs.get('class','').split():story.append(PageBreak())
        if node.tag in ('h2','h3'):
            story.append(Paragraph(inline(node),heading));return
        if node.tag=='p':
            story.append(Paragraph(inline(node),normal));return
        if node.tag=='table':table(node);return
        if node.tag in ('ol','ul'):
            number=0
            for child in node.children:
                if isinstance(child,Node) and child.tag=='li':
                    number+=1
                    prefix=f'{number}. ' if node.tag=='ol' else '• '
                    story.append(Paragraph(prefix+inline(child),normal))
            return
        if node.tag=='div' and 'respuesta' in node.attrs.get('class','').split():
            lines=Table([[''],['']],colWidths=[width],rowHeights=[20,20])
            lines.setStyle(TableStyle([('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#9baab8'))]))
            story.extend([lines,Spacer(1,10)]);return
        for child in node.children:visit(child)

    parser=DocumentParser();parser.feed(intro+item['html'])
    for node in parser.root.children:visit(node)
    def footer(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#cbd5e1'));canvas.line(44,40,A4[0]-44,40)
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#475467'))
        canvas.drawString(44,27,f"SIOE · {item['id']} · {course}")
        canvas.drawRightString(A4[0]-44,27,f'Página {doc.page}');canvas.restoreState()
    doc=SimpleDocTemplate(stream,pagesize=A4,leftMargin=44,rightMargin=44,topMargin=40,bottomMargin=55,title=f"{item['name']} - {course}",author='Sistema Integral de Orientación Educacional')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    stream.seek(0);return stream
