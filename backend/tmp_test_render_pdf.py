import asyncio
from app.crawl.browser import BrowserRenderService

async def main():
    html = "<html><body><h1>Test PDF</h1><p>Hello world</p></body></html>"
    pdf = await BrowserRenderService.render_pdf(html)
    if pdf:
        print('PDF bytes:', len(pdf))
    else:
        print('PDF generation failed')

asyncio.run(main())
