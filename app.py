from flask import Flask, render_template, request, jsonify, Response
import numpy as np
import json
import csv
import io
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

HISTORY_FILE = Path("history.json")

def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def generate_random_numbers(min_val, max_val, count, distribution='uniform', seed=None, precision=6):
    if seed is not None:
        np.random.seed(int(seed))
    
    if distribution == 'uniform':
        numbers = np.random.uniform(min_val, max_val, count)
    elif distribution == 'normal':
        mean = (min_val + max_val) / 2
        std = (max_val - min_val) / 6
        numbers = np.random.normal(mean, std, count)
        numbers = np.clip(numbers, min_val, max_val)
    elif distribution == 'exponential':
        scale = (max_val - min_val) / 3
        numbers = np.random.exponential(scale, count) + min_val
        numbers = np.clip(numbers, min_val, max_val)
    elif distribution == 'poisson':
        lam = (min_val + max_val) / 2
        numbers = np.random.poisson(lam, count).astype(float)
        numbers = np.clip(numbers, min_val, max_val)
    else:
        numbers = np.random.uniform(min_val, max_val, count)
    
    return [round(float(num), precision) for num in numbers]

def calculate_statistics(numbers):
    if not numbers:
        return {}
    
    arr = np.array(numbers)
    return {
        'mean': round(float(np.mean(arr)), 6),
        'std': round(float(np.std(arr)), 6),
        'min': round(float(np.min(arr)), 6),
        'max': round(float(np.max(arr)), 6),
        'median': round(float(np.median(arr)), 6),
        'range': round(float(np.max(arr) - np.min(arr)), 6)
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    min_val = float(data.get('min', 0))
    max_val = float(data.get('max', 1))
    count = int(data.get('count', 1))
    distribution = data.get('distribution', 'uniform')
    seed = data.get('seed')
    precision = int(data.get('precision', 6))
    
    if min_val >= max_val:
        return jsonify({'error': '最小值必须小于最大值'}), 400
    
    if count < 1 or count > 100:
        return jsonify({'error': '数量必须在1-100之间'}), 400
    
    if precision < 1 or precision > 10:
        return jsonify({'error': '精度必须在1-10之间'}), 400
    
    numbers = generate_random_numbers(min_val, max_val, count, distribution, seed, precision)
    statistics = calculate_statistics(numbers)
    
    history = load_history()
    entry = {
        'timestamp': datetime.now().isoformat(),
        'min': min_val,
        'max': max_val,
        'count': count,
        'distribution': distribution,
        'seed': seed,
        'precision': precision,
        'numbers': numbers,
        'statistics': statistics
    }
    history.insert(0, entry)
    
    if len(history) > 50:
        history = history[:50]
    
    save_history(history)
    
    return jsonify({
        'numbers': numbers,
        'statistics': statistics,
        'history': history
    })

@app.route('/history')
def get_history():
    history = load_history()
    return jsonify(history)

@app.route('/clear-history', methods=['POST'])
def clear_history():
    save_history([])
    return jsonify({'message': '历史记录已清空'})

@app.route('/export-history')
def export_history():
    history = load_history()
    
    if not history:
        return jsonify({'error': '没有可导出的历史记录'}), 400
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['时间戳', '最小值', '最大值', '数量', '分布', '种子', '精度', '生成的数字', '平均值', '标准差', '最小值', '最大值', '中位数', '范围'])
    
    for entry in history:
        numbers_str = '; '.join([str(num) for num in entry['numbers']])
        stats = entry.get('statistics', {})
        writer.writerow([
            entry['timestamp'],
            entry['min'],
            entry['max'],
            entry['count'],
            entry.get('distribution', 'uniform'),
            entry.get('seed', ''),
            entry.get('precision', 6),
            numbers_str,
            stats.get('mean', ''),
            stats.get('std', ''),
            stats.get('min', ''),
            stats.get('max', ''),
            stats.get('median', ''),
            stats.get('range', '')
        ])
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=random_history_{timestamp}.csv'
        }
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)