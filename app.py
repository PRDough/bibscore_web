from flask import Flask, render_template, request, send_from_directory
import os
import pandas as pd
import bibtexparser
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 清洗函数
def clean_text(text):
    if pd.isna(text):
        return ""
    text = re.sub(r"\$_ ?(?:extrm|textrm)?(\d)\$", r"\1", text)
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"\\%", "%", text)
    text = re.sub(r"\\n", " ", text)
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"\\t", " ", text)
    text = re.sub(r"\\&", "&", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"CO\s*2", "CO2", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# 打分函数
def score_entry(keywords, weights):
    if pd.isna(keywords):
        return 0
    keywords = keywords.lower()
    score = 0
    for keyword, weight in weights.items():
        score += keywords.count(keyword.lower()) * weight
    return score

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        bib_file = request.files.get("bibfile")
        raw_input = request.form.get("weights", "")
        weights = {}

        for line in raw_input.splitlines():
            if ':' in line:
                try:
                    k, v = line.split(':')
                    weights[k.strip()] = int(v.strip())
                except:
                    continue

        filename = None
        headers = None

        if bib_file:
            filename = secure_filename(bib_file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            bib_file.save(filepath)

            with open(filepath, encoding="utf-8") as bibtex_file:
                bib_database = bibtexparser.load(bibtex_file)
            entries = bib_database.entries
            df = pd.DataFrame(entries)

            # 清洗字段
            for col in ['title', 'abstract', 'keywords']:
                if col in df.columns:
                    df[col] = df[col].apply(clean_text)
                else:
                    df[col] = ""

            # 打分
            df['score'] = df['keywords'].apply(lambda x: score_entry(x, weights))

            # 排序保存
            df_sorted = df.sort_values('score', ascending=False)
            df_sorted.to_csv("last_upload.csv", index=False)
            headers = list(df_sorted.columns)

            return render_template(
                "index.html",
                headers=headers,
                weights_text=raw_input,
                uploaded_filename=filename
            )

    return render_template("index.html", headers=None, weights_text="", uploaded_filename=None)

@app.route("/download", methods=["POST"])
def download():
    selected_fields = request.form.getlist("fields")
    df = pd.read_csv("last_upload.csv")
    df_filtered = df[selected_fields]
    output_path = os.path.join(OUTPUT_FOLDER, "filtered_output.csv")
    df_filtered.to_csv(output_path, index=False)
    return send_from_directory(OUTPUT_FOLDER, "filtered_output.csv", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
