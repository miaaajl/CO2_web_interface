from flask import Flask, render_template, request, send_file
import storage_rate_target as srt
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    # 从表单获取用户输入
    start_year = int(request.form['start_year'])
    start_q = float(request.form['start_q'])
    start_qt = float(request.form['start_qt'])
    target_year = int(request.form['target_year'])
    target_s = float(request.form['target_s'])
    Pr_range = list(map(float, request.form['Pr_range'].split(',')))
    Qr_range = list(map(float, request.form['Qr_range'].split(',')))
    Rr_list = list(map(float, request.form['Rr_list'].split(',')))
    w = float(request.form['w'])
    year_rate_change = int(request.form['year_rate_change'])

    # 调用计算和绘图逻辑
    srt.main(start_year, start_q, start_qt, target_year, target_s, Pr_range, Qr_range, Rr_list, w, year_rate_change)
    
    # 渲染结果页面
    return render_template('results.html')


@app.route('/download_plot')
def download_plot():
    # 提供图表下载
    path = 'instance/data/results.png'
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
