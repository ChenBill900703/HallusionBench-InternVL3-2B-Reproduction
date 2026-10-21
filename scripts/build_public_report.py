"""Build an image-safe Chinese report from the maintained research documents."""
import html, os, re
from pathlib import Path
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, KeepTogether
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/HallusionBench_Research_Report_zhTW.pdf'
FONT=os.environ.get('HB_REPORT_FONT',r'C:/Windows/Fonts/msjh.ttc')
BOLD=os.environ.get('HB_REPORT_BOLD_FONT',r'C:/Windows/Fonts/msjhbd.ttc')
BLUE=colors.HexColor('#153C64'); TEAL=colors.HexColor('#07827C'); MUTED=colors.HexColor('#526477')
def rich(s):
    s=html.escape(s)
    s=re.sub(r'!\[([^\]]*)\]\([^)]+\)',r'\1',s)
    s=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'<link href="\2" color="#07827C">\1</link>',s)
    s=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',s)
    s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'`([^`]+)`',r'\1',s)
    return s.replace('—','-').replace('–','-').replace('‑','-')
def styles():
    pdfmetrics.registerFont(TTFont('HB',FONT,subfontIndex=0))
    pdfmetrics.registerFont(TTFont('HBB',BOLD,subfontIndex=0))
    pdfmetrics.registerFontFamily('HB',normal='HB',bold='HBB',italic='HB',boldItalic='HBB')
    common=dict(fontName='HB',wordWrap='CJK',textColor=BLUE,allowWidows=0,allowOrphans=0)
    return {
      'body':ParagraphStyle('body',fontSize=10.4,leading=17,spaceAfter=8,**common),
      'h1':ParagraphStyle('h1',fontSize=20,leading=28,spaceAfter=16,fontName='HBB',wordWrap='CJK',textColor=BLUE),
      'h2':ParagraphStyle('h2',fontSize=15,leading=22,spaceBefore=15,spaceAfter=10,keepWithNext=True,fontName='HBB',wordWrap='CJK',textColor=BLUE),
      'h3':ParagraphStyle('h3',fontSize=12,leading=19,spaceBefore=11,spaceAfter=7,keepWithNext=True,fontName='HBB',wordWrap='CJK',textColor=TEAL),
      'cell':ParagraphStyle('cell',fontSize=8.7,leading=13.3,**common),
      'small':ParagraphStyle('small',fontSize=8.5,leading=13,spaceAfter=7,**common),
      'caption':ParagraphStyle('caption',fontSize=9,leading=14,alignment=TA_CENTER,spaceAfter=12,**common),
      'cover':ParagraphStyle('cover',fontSize=30,leading=42,fontName='HBB',textColor=BLUE,wordWrap='CJK'),
    }
def table(lines,st,width):
    data=[]
    for line in lines:
        cells=[c.strip() for c in line.strip().strip('|').split('|')]
        if all(re.fullmatch(r':?-{3,}:?',c) for c in cells): continue
        data.append([Paragraph(rich(c),st['cell']) for c in cells])
    n=max(map(len,data)); data=[r+[Paragraph('',st['cell'])]*(n-len(r)) for r in data]
    if n==2: widths=[width*.25,width*.75]
    elif n==3: widths=[width*.32,width*.32,width*.36]
    elif n==4: widths=[width*.27,width*.24,width*.20,width*.29]
    else: widths=[width/n]*n
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DFECF5')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F5F8FA')]),('LINEBELOW',(0,0),(-1,0),.8,TEAL),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    return [t,Spacer(1,9)]
def markdown(path,st,width):
    lines=path.read_text(encoding='utf-8').splitlines(); out=[]; i=0; buffer=[]
    def flush():
        if buffer: out.append(Paragraph(rich(' '.join(buffer)),st['body'])); buffer.clear()
    while i<len(lines):
        line=lines[i].strip()
        if not line: flush(); i+=1; continue
        if line.startswith('|'):
            flush(); block=[]
            while i<len(lines) and lines[i].strip().startswith('|'): block.append(lines[i]); i+=1
            out.extend(table(block,st,width)); continue
        if line.startswith('```'):
            flush(); i+=1; block=[]
            while i<len(lines) and not lines[i].strip().startswith('```'):
                text=lines[i].replace(' ', '\u00a0')
                block.append(Paragraph(rich(text) or '&#160;',st['small'])); i+=1
            out.append(KeepTogether(block))
            i+=1; continue
        im=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',line)
        if im:
            flush(); p=(path.parent/im[2]).resolve()
            assert p.parent==ROOT/'stage2/figures' and p.suffix=='.png','Only the eight original analysis charts may be embedded'
            with PILImage.open(p) as image: w,h=image.size
            wout=min(width,450); hout=wout*h/w
            if hout>270: wout*=270/hout; hout=270
            out.append(KeepTogether([Image(str(p),width=wout,height=hout),Paragraph(rich(im[1]),st['caption'])])); i+=1; continue
        if line.startswith('#'):
            flush(); level=len(line)-len(line.lstrip('#')); title=line.lstrip('#').strip()
            if level==1: out.append(Paragraph(rich(title),st['h1']))
            else: out.append(Paragraph(rich(title),st['h2' if level==2 else 'h3']))
            i+=1; continue
        if line.startswith('- '):
            flush(); out.append(Paragraph('• '+rich(line[2:]),st['body'])); i+=1; continue
        buffer.append(line.lstrip('> ')); i+=1
    flush(); return out
def footer(canvas,doc):
    canvas.saveState(); w,h=A4
    canvas.setStrokeColor(colors.HexColor('#D8E3EA')); canvas.line(48,43,w-48,43)
    canvas.setFont('HB',8); canvas.setFillColor(MUTED)
    canvas.drawString(48,29,'HallusionBench | InternVL3-2B | 研究整理')
    canvas.drawRightString(w-48,29,str(doc.page))
    if doc.page>1: canvas.drawString(48,h-31,'原論文與單模型復現分開呈現')
    canvas.restoreState()
def main():
    st=styles(); width=A4[0]-96; OUT.parent.mkdir(exist_ok=True)
    story=[Spacer(1,45),Paragraph('看圖模型<br/>真的看懂了嗎？',st['cover']),Spacer(1,18),
      Paragraph('HallusionBench（CVPR 2024）<br/>論文四大重點與 InternVL3-2B 單模型復現',st['h2']),Spacer(1,20),
      Paragraph('用一張 RTX 3070 Ti 8GB，完成 1,129 題評估。',st['body']),
      Paragraph('2026-10-21 · Stage 3 發布版',st['small']),Spacer(1,20)]
    key=[['單題接受率 All','整組全對 qAcc','同圖全對 fAcc'],['54.65%','22.42%','28.90%']]
    story+=table(['|'+ '|'.join(r)+'|' for r in key],st,width)
    story+=[Spacer(1,18),Paragraph('怎麼讀這份報告？',st['h3']),
      Paragraph('第一部分依四個重點說明原論文：摘要、目的、方法與成果。第二部分整理本次實作、八張分析圖、案例及可信度。文獻數字標為 Published Results；只有 InternVL3-2B 是本次實測。',st['body']),
      Paragraph('All 包含 63 題官方 VS 無圖接受特例；診斷分類不等於模型內部成因。沒有獨立人工判分驗證。',st['body']),
      Paragraph('此版不含第三方原始圖片。原本地含圖報告已核對為 20 頁；本版另行排版，頁數與該封存不同。完整原始回答、判分及來源版本請見專案資料。',st['small']),
      Paragraph('<link href="https://github.com/ChenBill900703/HallusionBench-InternVL3-2B-Reproduction" color="#07827C">GitHub：ChenBill900703 / HallusionBench-InternVL3-2B-Reproduction</link>',st['small']),
      PageBreak()]
    for n,rel in enumerate(['docs/PAPER_SUMMARY_zhTW.md','docs/REPRODUCTION_SUMMARY_zhTW.md','docs/DATA_GUIDE_zhTW.md']):
        if n: story.append(PageBreak())
        story.extend(markdown(ROOT/rel,st,width))
    doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=53,bottomMargin=57,
       title='HallusionBench：論文整理與 InternVL3-2B 單模型復現',author='ChenBill900703')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    from pypdf import PdfReader
    print(str(OUT)); print('Pages:',len(PdfReader(OUT).pages))
if __name__=='__main__': main()
