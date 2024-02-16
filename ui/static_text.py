class S:
    md_content_help = \
"""
# Content Tab
## Workflow overview
 - Data arrives to app (Smithproxy must be set specifically)
 - **Skip** will let traffic pass without displaying or changes
 - Received content data is displayed on the left side in hex + ascii form
 - Script in active slot (top-right text widget) is intended to process data received previously
 - Checked **Auto-Execute** will make script to run automatically on data arrival
 - The 'content_replacement' variable may be set to replace original payload
 - Clicking **Process Request** confirms changes made and response is sent to proxy
 - Any problems or script outputs are displayed in right-bottom text widget
"""