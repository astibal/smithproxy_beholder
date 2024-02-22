class S:
    txt_skip_checked = "The 'Skip' button is now checked - all payload is silently confirmed"
    txt_sample_empty = "Click sample button to load bytes in here."
    txt_skip_unchecked = "Waiting for content from smithproxy to be processed..."
    py_default_script = \
        "# Available variables:\n" \
        "# -- INPUT variables --\n" \
        "#  content_data - bytes of content data received from the proxy\n" \
        "#  content_side - 'L' or 'R', if from client('L'), or server respectively ('R')\n" \
        "#  session_id - unique proxy session identifier\n" \
        "#  session_label - string containing IPs and ports\n" \
        "# -- STORAGE --\n" \
        "#  samples - quick access to byte samples (dict(int), starting with 1)\n" \
        "#  storage - dict with persistent memory data\n" \
        "#  storage_lock - always access storage with the lock! ('with storage_lock:')\n" \
        "# -- OUTPUT variables --\n" \
        "#  content_replacement - None or bytes used by proxy to replace original content\n" \
        "#  auto_process - set to True to trigger 'Process' action after script finishes." \
        "\n\n" \
        "# info function example:\n" \
        "def info():\n" \
        "    if content_data:\n" \
        "        print(f'{session_id}: {session_label} recv {len(content_data)}B from {content_side}')\n" \
        "\n\n"

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
