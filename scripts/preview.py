from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
ROOT=Path(__file__).resolve().parents[1]/'dist'
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**k): super().__init__(*a,directory=str(ROOT),**k)
 def do_GET(self):
  u=urlparse(self.path)
  if u.path=='/__qa':
   size=320 if parse_qs(u.query).get('width')==['320'] else 390
   target=parse_qs(u.query).get('page',['/'])[0]
   if target not in ['/', '/products/cursay','/products/jjikgo','/products/yeoun','/products/moru']:target='/'
   body=f'<html><body style="margin:0;background:#ccc"><iframe title="Mobile preview" src="{target}" style="width:{size}px;height:844px;border:0;display:block;margin:auto"></iframe></body></html>'.encode()
   self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(body);return
  if '.' not in u.path and (ROOT/(u.path.lstrip('/')+'.html')).is_file(): self.path=u.path+'.html'
  super().do_GET()
HTTPServer(('127.0.0.1',8767),Handler).serve_forever()
