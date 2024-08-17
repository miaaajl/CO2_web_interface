import os
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

# 设置 Matplotlib 后端为 Agg
import matplotlib
matplotlib.use('Agg')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# 确保 instance 目录存在
if not os.path.exists('instance'):
    os.makedirs('instance')

# 使用绝对路径指定数据库文件
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    plots = db.relationship('Plot', backref='user', lazy=True)

class Plot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        new_user = User(email=email, password=password)
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            flash('Email address already exists')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        start_year = int(request.form['start_year'])
        start_q = float(request.form['start_q'])
        start_qt = float(request.form['start_qt'])
        target_s = float(request.form['target_s'])
        pr_min = int(request.form['pr_min'])
        pr_max = int(request.form['pr_max'])
        qr_min = float(request.form['qr_min'])
        qr_max = float(request.form['qr_max'])
        rr_values = list(map(float, request.form['rr_values'].split(',')))
        year_rate_change = int(request.form['year_rate_change'])
        historical_data = np.loadtxt('data/USdata.txt', delimiter='\t')
        aspect_ratio = request.form['aspect_ratio']
        legend_position = request.form['legend_position']
        show_grid = 'show_grid' in request.form
        background_color = request.form['background_color']
        line_color_scale = request.form['line_color_scale']
        show_markers = 'show_markers' in request.form

        # Calculate storage
        results = calculate_storage(
            start_year, start_q, start_qt, target_s,
            pr_min, pr_max, qr_min, qr_max, rr_values, year_rate_change
        )
        
        best_peak_year = min(results['peak_years'])
        best_total_stored = min(results['total_storages'])
        best_growth_rate = min(rr_values)
        
        # Create plots
        cum_storage_graph, storage_rate_graph = create_plots(
            results, historical_data, year_rate_change, aspect_ratio,
            legend_position, show_grid, background_color, line_color_scale, show_markers
        )
        
        if 'user_id' in session:
            new_plot = Plot(data=cum_storage_graph, user_id=session['user_id'])
            db.session.add(new_plot)
            db.session.commit()
        
        return render_template('plot.html', cum_storage_graph=cum_storage_graph, storage_rate_graph=storage_rate_graph, best_peak_year=best_peak_year, best_total_stored=best_total_stored, best_growth_rate=best_growth_rate)
    return render_template('dashboard.html')

@app.route('/user_plots')
def user_plots():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    plots = Plot.query.filter_by(user_id=user_id).all()
    return render_template('user_plots.html', plots=plots)

def calculate_storage(start_year, start_q, start_qt, target_s, pr_min, pr_max, qr_min, qr_max, rr_values, year_rate_change):
    years = np.arange(1970, 2101)
    results = {
        'years': years,
        'growth_rates': rr_values,
        'peak_years': [],
        'storage_trajectories': [],
        'total_storages': [],
        'storage_rates': []
    }
    
    for r in rr_values:
        best_peak_year = None
        best_total_stored = None
        min_error = float('inf')
        
        for peak_year in range(pr_min, pr_max + 1):
            for total_stored in np.logspace(np.log10(qr_min), np.log10(qr_max), num=100):
                rate_change = start_q * np.exp(start_qt * (year_rate_change - start_year))
                C = total_stored - rate_change
                pt = C / (1 + np.exp(r * (peak_year - years)))
                qt = np.gradient(pt)
                error = np.abs(pt[np.where(years == 2050)[0][0]] - target_s)
                
                if error < min_error:
                    min_error = error
                    best_peak_year = peak_year
                    best_total_stored = total_stored
        
        results['peak_years'].append(best_peak_year)
        results['total_storages'].append(best_total_stored)
        
        rate_change = start_q * np.exp(start_qt * (year_rate_change - start_year))
        C = best_total_stored - rate_change
        pt = C / (1 + np.exp(r * (best_peak_year - years)))
        qt = np.gradient(pt)
        results['storage_trajectories'].append(pt)
        results['storage_rates'].append(qt)
    
    return results

def create_plots(results, historical_data, year_rate_change, aspect_ratio, legend_position, show_grid, background_color, line_color_scale, show_markers):
    # 获取2030年的数据索引
    index_2030 = np.where(historical_data[:, 0] == 2030)[0][0]
    
    # 历史数据只绘制到2030年之前
    historical_years = historical_data[:index_2030+1, 0]
    historical_cumulative = historical_data[:index_2030+1, 2]
    
    # Create cumulative storage plot
    if aspect_ratio == 'custom':
        width = int(request.form['custom_aspect_ratio_width'])
        height = int(request.form['custom_aspect_ratio_height'])
        plt.figure(figsize=(width, height))
    else:
        aspect_ratio_map = {
            '1:1': (8, 8),
            '4:3': (12, 9),
            '16:9': (16, 9)
        }
        plt.figure(figsize=aspect_ratio_map[aspect_ratio])
    
    years = results['years']
    future_years = years[years >= 2030]
    
    for i, trajectory in enumerate(results['storage_trajectories']):
        future_trajectory = trajectory[years >= 2030]
        if show_markers:
            plt.plot(future_years, future_trajectory, label=f'R: {results["growth_rates"][i]}', marker='o')
        else:
            plt.plot(future_years, future_trajectory, label=f'R: {results["growth_rates"][i]}')
    
    # Plot historical data up to 2030
    plt.plot(historical_years, historical_cumulative, '-ok', markerfacecolor='k', markersize=2, linewidth=1, label='Historical')
    
    plt.xlabel('Year')
    plt.ylabel('Cumulative Storage (Gt)')
    plt.title('Cumulative CO2 Storage Over Time')
    plt.yscale('log')  # 使用对数刻度

    if show_grid:
        plt.grid(True)
    
    plt.legend(loc=legend_position)
    plt.gca().set_facecolor(background_color)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    cum_storage_graph = base64.b64encode(buf.getvalue()).decode()
    buf.close()
    
    # Create storage rate plot
    if aspect_ratio == 'custom':
        width = int(request.form['custom_aspect_ratio_width'])
        height = int(request.form['custom_aspect_ratio_height'])
        plt.figure(figsize=(width, height))
    else:
        aspect_ratio_map = {
            '1:1': (8, 8),
            '4:3': (12, 9),
            '16:9': (16, 9)
        }
        plt.figure(figsize=aspect_ratio_map[aspect_ratio])
    
    for i, rate in enumerate(results['storage_rates']):
        future_rate = rate[years >= 2030]
        if show_markers:
            plt.plot(future_years, future_rate, label=f'R: {results["growth_rates"][i]}', marker='o')
        else:
            plt.plot(future_years, future_rate, label=f'R: {results["growth_rates"][i]}')
    
    plt.xlabel('Year')
    plt.ylabel('Storage Rate (Gt/year)')
    plt.title('CO2 Storage Rate Over Time')
    
    if show_grid:
        plt.grid(True)
    
    plt.legend(loc=legend_position)
    plt.gca().set_facecolor(background_color)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    storage_rate_graph = base64.b64encode(buf.getvalue()).decode()
    buf.close()
    
    return cum_storage_graph, storage_rate_graph



if __name__ == '__main__':
    if not os.path.exists('database.db'):
        with app.app_context():
            db.create_all()
    app.run(debug=True)
