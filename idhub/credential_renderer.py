#!/usr/bin/env python3

import re
import json

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

    def walk_dict(data_dict, prefix=""):
        html_lines = []
        for key, value in data_dict.items():
            if key in ["@context", "type", "id"] and not prefix:
                continue

            current_path = f"{prefix}.{key}" if prefix else key
            clean_name = re.sub('([A-Z])', r' \1', key).title()

            if isinstance(value, dict):
                html_lines.append(f'<div class="col-12"><h4 class="mt-4 mb-3" style="color: #545f71;"><i class="bi bi-box-seam me-2"></i>{clean_name}</h4></div>')
                html_lines.append('<div class="col-12"><div class="component-card"><div class="row g-3">')
                html_lines.append(walk_dict(value, current_path))
                html_lines.append('</div></div></div>')

            elif isinstance(value, list):
                html_lines.append(f'<div class="col-12"><h4 class="mt-4 mb-3" style="color: #545f71;"><i class="bi bi-collection me-2"></i>{clean_name}</h4></div>')
                html_lines.append(f"{{{{#each {current_path}}}}}")
                html_lines.append('<div class="col-12"><div class="component-card"><div class="row g-3">')

                if len(value) > 0 and isinstance(value[0], dict):
                    html_lines.append(walk_dict(value[0], "this"))
                else:
                    html_lines.append('<div class="col-12 info-value fw-bold">{{this}}</div>')

                html_lines.append('</div></div></div>')
                html_lines.append("{{/each}}")

            else:
                html_lines.append(f"""
                <div class="col-md-6 col-lg-4">
                    <div class="info-row row">
                        <div class="col-12 info-label text-muted">{clean_name}</div>
                        <div class="col-12 info-value fw-bold">{{{{{current_path}}}}}</div>
                    </div>
                </div>""")

        return "\n".join(html_lines)

    # Build the dynamic HTML body
    subject_data = raw_vc.get("credentialSubject", {})
    if isinstance(subject_data, list):
        subject_html = f"""
        {{{{#each credentialSubject}}}}
            <div class="component-card mb-4"><div class="row g-3">
                {walk_dict(subject_data[0], "this")}
            </div></div>
        {{{{/each}}}}
        """
    else:
        subject_html = walk_dict(subject_data, "credentialSubject")

    # wrap
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
                    <div class="col-md-8 info-value"><div class="hash-value">{{{{id}}}}</div></div>
                </div>
                <div class="info-row row mt-2">
                    <div class="col-md-4 info-label">Types</div>
                    <div class="col-md-8 info-value">
                        {{{{#each type}}}}<span class="badge bg-secondary me-1">{{{{this}}}}</span>{{{{/each}}}}
                    </div>
                </div>
            </div>

            <div class="col-lg-6">
                <h2 class="section-title">Issuer Information</h2>
                <div class="info-row row">
                    <div class="col-md-4 info-label">Issuer ID</div>
                    <div class="col-md-8 info-value"><div class="hash-value">{{{{issuer.id}}}}</div></div>
                </div>
                <div class="info-row row mt-2">
                    <div class="col-md-4 info-label">Valid From</div>
                    <div class="col-md-8 info-value fw-bold">{{{{validFrom}}}}</div>
                </div>
            </div>
        </div>

        <h2 class="section-title mt-5">Subject Payload</h2>
        <div class="row g-3">
            {subject_html}
        </div>

        <footer>
            <p class="mb-0">&copy; eReuse Verified Data Record</p>
        </footer>
    </div>
</body>
</html>"""

    return final_html.replace('    ', '').replace('\n', '')
