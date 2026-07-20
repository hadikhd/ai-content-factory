def render_timeline(completed_steps, pipeline_order, step_details=None) -> str:
    completed_steps = completed_steps or []
    pipeline_order = pipeline_order or []

    html = "<div class='timeline'>"

    for step in pipeline_order:
        if step in completed_steps:
            status = "✅"
        else:
            status = "⏳"

        html += f"<div>{status} {step}</div>"

    html += "</div>"
    return html
