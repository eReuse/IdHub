import html
import re
from django.template.loader import render_to_string

def generate_universal_template(raw_vc):
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

    context = {
        "vc_id": vc_id,
        "types_html": types_html,
        "issuer_id_escaped": issuer_id_escaped,
        "valid_from": valid_from,
        "subject_html": subject_html,
    }

    final_html = render_to_string("credentials/universal_untp_template.html", context)
    return final_html.replace('    ', '').replace('\n', '')
