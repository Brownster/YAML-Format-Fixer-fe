from flask import Flask, request, render_template, send_from_directory
from werkzeug.utils import secure_filename, safe_join
import os
import difflib
import gunicorn

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp/'

def adjust_comment_indentation(lines):
    new_lines = []  # Ensure new_lines is initialized
    for i, line in enumerate(lines):
        stripped_line = line.lstrip()
        if stripped_line.startswith("#"):
            next_line_index = i + 1
            while next_line_index < len(lines) and not lines[next_line_index].strip():
                next_line_index += 1
            if next_line_index < len(lines):
                next_line_indentation = len(lines[next_line_index]) - len(lines[next_line_index].lstrip())
                line = " " * next_line_indentation + stripped_line
        new_lines.append(line)
    return new_lines  # Return the new_lines list

def process_yaml_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        original_lines = file.readlines()

    modified_lines = [line.rstrip() + '\n' for line in original_lines]
    if modified_lines and not modified_lines[0].strip().startswith('---'):
        modified_lines.insert(0, '---\n')

    modified_lines = adjust_comment_indentation(modified_lines)
    if modified_lines[-1].strip() == '---':
        modified_lines.pop()

    modified_lines = [line for i, line in enumerate(modified_lines) if i == 0 or not (line.isspace() and modified_lines[i - 1].isspace())]

    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(modified_lines)

    change_report = difflib.unified_diff(original_lines, modified_lines, fromfile=file_path, tofile=file_path, lineterm='\n')
    return ''.join(change_report)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Process the file and generate the change report
    change_log = process_yaml_file(filepath)

    return render_template('results.html', change_log=change_log, yaml_file=filename)

def process_diff_to_html(diff_output):
    html_lines = []
    for line in diff_output.split('\n'):
        if line.startswith('+'):
            html_lines.append(f'<div class="inserted">{line}</div>')
        elif line.startswith('-'):
            html_lines.append(f'<div class="deleted">{line}</div>')
        else:
            html_lines.append(f'<div class="context">{line}</div>')
    return '\n'.join(html_lines)


@app.route('/downloads/<filename>')
def download_file(filename):
    change_log_html = process_diff_to_html(change_log)
    return render_template('results.html', change_log_html=change_log_html, yaml_file=filename)


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=8000)  # Run the app on port 8000

