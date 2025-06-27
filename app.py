from datetime import date
from flask import Flask, request, render_template_string

from yt_channel_analyzer.storage import load_data
from yt_channel_analyzer.analysis import hero_hub_help_matrix

app = Flask(__name__)

TEMPLATE = """
<!doctype html>
<title>YouTube Channel Analyzer</title>
<h1>YouTube Channel Analyzer</h1>
<form method="get">
  Start date: <input type="date" name="start_date" value="{{ request.args.get('start_date', '') }}">
  End date: <input type="date" name="end_date" value="{{ request.args.get('end_date', '') }}">
  <input type="submit" value="Filter">
</form>
<table border="1">
  <tr><th>Channel</th><th>Hero (videos/views)</th><th>Hub (videos/views)</th><th>Help (videos/views)</th></tr>
  {% for r in results %}
    <tr>
      <td>{{ r.name }}</td>
      <td>{{ r.counts.hero }} / {{ r.views.hero }}</td>
      <td>{{ r.counts.hub }} / {{ r.views.hub }}</td>
      <td>{{ r.counts.help }} / {{ r.views.help }}</td>
    </tr>
  {% endfor %}
</table>
"""

@app.route('/')
def index():
    data = load_data()
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    start_date = date.fromisoformat(start) if start else None
    end_date = date.fromisoformat(end) if end else None
    results = []
    for comp in data.get('competitors', {}).values():
        counts, views = hero_hub_help_matrix(comp, start_date, end_date)
        results.append({'name': comp['name'], 'counts': counts, 'views': views})
    return render_template_string(TEMPLATE, results=results)


if __name__ == '__main__':
    app.run(debug=True)
