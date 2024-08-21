import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib.cm as cm

import json

def load_us_data():
    """
    加载 USdata.txt 文件，返回年份、储存率和累计储存量
    """
    data = np.loadtxt('data/USdata.txt')
    years = data[:, 0]  # 年份
    qinj = data[:, 1]   # 储存率
    Q = data[:, 2] / 1000  # 累计储存量，转换为Gt
    return years, qinj, Q

def storage_rate_target_fit(start_year, start_q, start_qt, target_year, target_s, Pr_range, Qr_range, Rr_list):
    """
    计算并拟合多个 Rr 对应的 peak_year 和 total_stored
    """
    peak_years = []
    total_stored_list = []

    # 使用 linspace 和 logspace 函数来生成 Pr_range 和 Qr_range
    Pr_range = np.linspace(Pr_range[0], Pr_range[1], int(Pr_range[2]))
    Qr_range = np.logspace(np.log10(Qr_range[0]), np.log10(Qr_range[1]), int(Qr_range[2]))

    for Rr in Rr_list:
        min_peak = np.zeros(len(Qr_range))
        qt_target = np.zeros(len(Qr_range))
        Qmin = np.zeros(1)

        for i in range(len(Qr_range)):
            fit_diff = np.zeros(len(Pr_range))
            for k in range(len(Pr_range)):
                # 计算累计存储量
                p = ((Qr_range[i] - start_q) / (1 + np.exp(Rr * (Pr_range[k] - start_year))))
                # 计算拟合差异
                fit_diff[k] = (p - start_q) ** 2

            rowk = np.argmin(fit_diff)
            min_peak[i] = Pr_range[rowk]
            
            # 计算存储速率差异
            q = (Qr_range[i] - start_q) * Rr * np.exp(Rr * (min_peak[i] - target_year)) / \
                ((1 + np.exp(Rr * (min_peak[i] - target_year))) ** 2)
            qt_target[i] = (target_s - q) ** 2

        ifit = np.argmin(qt_target)
        Qmin[0] = Qr_range[ifit]
        
        # 存储计算结果
        peak_years.append(min_peak[ifit])
        total_stored_list.append(Qmin[0])

    return peak_years, total_stored_list



def target_high(w, year_rate_change, rtargetmedium, peak_targetmedium, Qtargetmedium):
    """
    使用 peak_years 和 total_stored_list 进行后续计算并生成图表
    """
    inflection_times = []
    storage_rates = []
    
    for i in range(len(Qtargetmedium)):
        cum_2030 = np.exp(year_rate_change * w) * np.exp(-182.6431721)
        x2 = np.arange(year_rate_change, 2150)
        C = Qtargetmedium[i] - cum_2030
        
        yrate2 = (C * rtargetmedium[i] * np.exp(rtargetmedium[i] * (peak_targetmedium[i] - x2))) / \
                 ((1 + np.exp(rtargetmedium[i] * (peak_targetmedium[i] - x2))) ** 2)
        
        storage_rates.extend(yrate2)
        inflection_time_red = peak_targetmedium[i] - np.log(2 + np.sqrt(3)) / rtargetmedium[i]
        inflection_times.append(inflection_time_red)
    
    return inflection_times, storage_rates


def plot_results(years, Q, rtargetmedium, Qtargetmedium, peak_targetmedium, year_rate_change, w):
    """
    使用 Matplotlib 绘制累积存储量曲线图和存储速率曲线图
    """
    plt.figure(figsize=(18, 8))
    
    # 定义springcc颜色映射
    num_curves = len(Qtargetmedium)
    springcc = cm.spring(np.linspace(0, 1, num_curves + 1))

    # 累积存储量曲线图
    plt.subplot(1, 2, 1)
    plt.plot(years, Q, '-ok', markerfacecolor='k', markersize=2, linewidth=1, label='Historical Data')
    
    for i in range(len(Qtargetmedium)):
        cum_at_rate_change = np.exp(year_rate_change * w) * np.exp(-182.6431721)
        x2 = np.arange(year_rate_change, 2101)
        
        C = (Qtargetmedium[i] - cum_at_rate_change)
        pt = (C / (1 + np.exp(rtargetmedium[i] * (peak_targetmedium[i] - x2))))
        plt.plot(x2, pt, color=springcc[i + 1, :], label=f'{rtargetmedium[i]*100:.2f}% with {Qtargetmedium[i]:.1f} Gt')
    
    plt.title('Cumulative Storage over Time')
    plt.xlabel('Year')
    plt.ylabel('Cumulative Storage [Gt]')
    plt.yscale('log')
    plt.grid(True)
    plt.legend(loc='upper left')
    plt.text(2070, 5000, 'High', fontsize=14, fontweight='bold')

    # 存储速率曲线图
    plt.subplot(1, 2, 2)
    
    for i in range(len(Qtargetmedium)):
        cum_2030 = np.exp(year_rate_change * w) * np.exp(-182.6431721)
        x2 = np.arange(year_rate_change, 2151)
        
        C = (Qtargetmedium[i] - cum_2030)
        yrate2 = (C * rtargetmedium[i] * np.exp(rtargetmedium[i] * (peak_targetmedium[i] - x2))) / \
                 ((1 + np.exp(rtargetmedium[i] * (peak_targetmedium[i] - x2))) ** 2)
        
        # 绘制存储速率曲线
        plt.plot(x2, yrate2, color=springcc[i + 1, :], label=f'{round(Qtargetmedium[i])} Gt, based on {rtargetmedium[i]*100:.1f}% Growth')
        
        # 计算并标记拐点
        inflection_time_red = peak_targetmedium[i] - np.log(2 + np.sqrt(3)) / rtargetmedium[i]
        y_inflect_red = (C * rtargetmedium[i] * np.exp(rtargetmedium[i] * (peak_targetmedium[i] - inflection_time_red))) / \
                        ((1 + np.exp(rtargetmedium[i] * (peak_targetmedium[i] - inflection_time_red))) ** 2)
        plt.plot(inflection_time_red, y_inflect_red, '.k', markersize=15)  # 黑色点标记拐点
    
    plt.title('Storage Rate over Time')
    plt.xlabel('Year')
    plt.ylabel('Storage Rate [Gt/year]')
    plt.grid(True)
    plt.legend(loc='upper left')

    # 将图片保存到 static/images 目录下
    image_path = 'static/images/results.png'
    plt.savefig(image_path)
    plt.close()  # 关闭图表以释放内存




def main(start_year, start_q, start_qt, target_year, target_s, Pr_range, Qr_range, Rr_list, w, year_rate_change):
    """
    主函数，执行整个计算流程
    """
    # 加载 USdata
    years, qinj, Q = load_us_data()

    # 拟合和计算多个Rr对应的peak_year和total_stored
    peak_years, total_stored_list = storage_rate_target_fit(start_year, start_q, start_qt, target_year, target_s, Pr_range, Qr_range, Rr_list)
    
    # 计算派生的参数
    rtargetmedium = Rr_list  # Rr_list 直接作为 rtargetmedium
    Qtargetmedium = total_stored_list  # 计算得到的 total_stored_list
    peak_targetmedium = peak_years  # 计算得到的 peak_years

    # 根据计算结果，继续进行高精度目标计算
    inflection_times, storage_rates = target_high(peak_years, total_stored_list, w, year_rate_change, rtargetmedium, peak_targetmedium, Qtargetmedium)
    
    # 绘制并保存结果图表，包含历史数据
    plot_results(peak_years, total_stored_list, inflection_times, storage_rates, years, Q, rtargetmedium, Qtargetmedium, peak_targetmedium, year_rate_change, w)

    # 保存结果到 JSON 文件
    with open('instance/data/results.json', 'w') as f:
        json.dump({
            'peak_years': peak_years,
            'total_stored_list': total_stored_list,
            'inflection_times': inflection_times,
            'storage_rates': storage_rates
        }, f)