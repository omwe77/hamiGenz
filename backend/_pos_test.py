import os, traceback
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from document_processor import DocumentProcessor
from form_understanding import detect_form_positions

up = '../data/uploads'
dp = DocumentProcessor(upload_dir=up)
for f in ['11e2e975.pdf', '21893005.pdf']:
    try:
        pages = dp.extract_text(os.path.join(up, f))
        print('====', f, 'pages:', [p['page_num'] for p in pages])
        for p in pages:
            if not p.get('text'):
                continue
            t = p['text']
            wb = dp._tesseract_word_boxes(os.path.join(up, f), p['page_num'])
            det = detect_form_positions(t, wb)
            print(' page', p['page_num'], 'is_form:', det['is_form'],
                  'fields:', det['field_count'], 'boxes:', len(wb))
            for fd in det['fields'][:8]:
                print('   ', repr(fd.get('label')), 'p%d' % fd.get('page'),
                      'X=%.0f Y=%.0f W=%.0f H=%.0f' % (
                          fd.get('x', 0), fd.get('y', 0), fd.get('w', 0), fd.get('h', 0)))
    except Exception:
        traceback.print_exc()
