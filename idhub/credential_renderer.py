import re

def generate_universal_template(raw_vc):
    css_styles = """
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/css/bootstrap.min.css" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" />
    <style>
      body { font-size: 0.875rem; background-color: #f8f9fa; display: flex; flex-direction: column; min-height: 100vh; padding: 20px;}
      .custom-container { background-color: #ffffff; border-radius: 10px; box-shadow: 0 0 20px rgba(0, 0, 0, 0.1); padding: 30px; margin: 0 auto; max-width: 1200px; flex-grow: 1; }
      .section-title { color: #7a9f4f; border-bottom: 2px solid #9cc666; padding-bottom: 10px; margin-bottom: 20px; font-size: 1.5em; margin-top: 30px;}
      .info-row { margin-bottom: 10px; align-items: baseline; }
      .info-label { font-weight: bold; color: #545f71; font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px;}
      .info-value { color: #333; word-break: break-word; }
      .hash-value { word-break: break-all; background-color: #f3f3f3; padding: 5px; border-radius: 4px; font-family: monospace; font-size: 0.9em; border: 1px solid #e0e0e0; display: inline-block;}
      .component-card { background-color: #f8f9fa; border-left: 4px solid #9cc666; margin-bottom: 15px; border-radius: 5px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
      footer { background-color: #545f71; color: #ffffff; text-align: center; padding: 15px 0; margin-top: 40px; border-radius: 8px;}
    </style>
    """

    def walk_dict(data_dict):
        html_lines = []
        for key, value in data_dict.items():
            if key in ["@context", "type", "id"]:
                continue

            raw_name = re.sub(r'([A-Z])', r' \1', str(key)).title()
            clean_name = html.escape(raw_name)

            if isinstance(value, dict):
                html_lines.append(
                    f'<div class="col-12"><h4 class="mt-4 mb-3" style="color: #545f71;"><i class="bi bi-box-seam me-2"></i>{clean_name}</h4></div>'
                )
                html_lines.append('<div class="col-12"><div class="component-card"><div class="row g-3">')
                html_lines.append(walk_dict(value))
                html_lines.append('</div></div></div>')

            elif isinstance(value, list):
                html_lines.append(
                    f'<div class="col-12"><h4 class="mt-4 mb-3" style="color: #545f71;"><i class="bi bi-collection me-2"></i>{clean_name}</h4></div>'
                )
                html_lines.append('<div class="col-12"><div class="component-card"><div class="row g-3">')

                for idx, item in enumerate(value):
                    if isinstance(item, dict):
                        if idx > 0:
                            html_lines.append('<hr class="my-3 text-muted">')
                        html_lines.append('<div class="col-12"><div class="row g-3">')
                        html_lines.append(walk_dict(item))
                        html_lines.append('</div></div>')
                    else:
                        escaped_item = html.escape(str(item))
                        html_lines.append(f'<div class="col-12 info-value fw-bold">{escaped_item}</div>')

                html_lines.append('</div></div></div>')

            else:
                escaped_val = html.escape(str(value))
                html_lines.append(f"""
                <div class="col-md-6 col-lg-4">
                    <div class="info-row row">
                        <div class="col-12 info-label text-muted">{clean_name}</div>
                        <div class="col-12 info-value fw-bold">{escaped_val}</div>
                    </div>
                </div>""")

        return "\n".join(html_lines)

    vc_id = html.escape(str(raw_vc.get("id", "N/A")))

    types = raw_vc.get("type", [])
    if isinstance(types, str):
        types = [types]
    types_html = "".join([f'<span class="badge bg-secondary me-1">{html.escape(str(t))}</span>' for t in types])

    issuer = raw_vc.get("issuer", {})
    issuer_id = issuer.get("id") if isinstance(issuer, dict) else issuer
    if not issuer_id:
        issuer_id = "N/A"
    issuer_id_escaped = html.escape(str(issuer_id))

    valid_from = html.escape(str(raw_vc.get("validFrom") or raw_vc.get("issuanceDate", "N/A")))

    subject_data = raw_vc.get("credentialSubject", {})
    if isinstance(subject_data, list):
        subject_html_parts = []
        for item in subject_data:
            subject_html_parts.append(
                f'<div class="component-card mb-4"><div class="row g-3">{walk_dict(item)}</div></div>'
            )
        subject_html = "\n".join(subject_html_parts)
    elif isinstance(subject_data, dict):
        subject_html = walk_dict(subject_data)
    else:
        subject_html = f'<div class="col-12 info-value">{html.escape(str(subject_data))}</div>'

    final_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {css_styles}
</head>
<body>
    <div class="custom-container">
        <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 border-bottom pb-3">
            <h1 class="text-center text-md-start mb-0" style="color: #545f71;">
                <i class="bi bi-shield-check me-2" style="color: #9cc666;"></i>Verified Credential
            </h1>
        </div>

        <div class="row g-4">
            <div class="col-lg-6">
                <h2 class="section-title">Details</h2>
                <div class="info-row row">
                    <div class="col-md-4 info-label">Credential ID</div>
                    <div class="col-md-8 info-value"><div class="hash-value">{vc_id}</div></div>
                </div>
                <div class="info-row row mt-2">
                    <div class="col-md-4 info-label">Types</div>
                    <div class="col-md-8 info-value">
                        {types_html}
                    </div>
                </div>
            </div>

            <div class="col-lg-6">
                <h2 class="section-title">Issuer Information</h2>
                <div class="info-row row">
                    <div class="col-md-4 info-label">Issuer ID</div>
                    <div class="col-md-8 info-value"><div class="hash-value">{issuer_id_escaped}</div></div>
                </div>
                <div class="info-row row mt-2">
                    <div class="col-md-4 info-label">Valid From</div>
                    <div class="col-md-8 info-value fw-bold">{valid_from}</div>
                </div>
            </div>
        </div>

        <h2 class="section-title mt-5">Subject Payload</h2>
        <div class="row g-3">
            {subject_html}
        </div>

        <footer>
            <p class="mb-0">&copy; eReuse</p>
        </footer>
    </div>
</body>
</html>"""

    return final_html.replace('    ', '').replace('\n', '')
