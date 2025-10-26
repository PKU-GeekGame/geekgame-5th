from flask import Flask, render_template, jsonify, request, send_from_directory
import sqlite3
import os
from pathlib import Path

app = Flask(__name__)

# 配置路径
BASE_DIR = Path(__file__).parent.parent
IMAGES_DIR = BASE_DIR / 'ACG' / 'flag2_images'
DB_PATH = Path(__file__).parent / 'annotations.db'

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS annotations (
            image_name TEXT PRIMARY KEY,
            label INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_image_list():
    """获取所有图片文件名并排序"""
    images = []
    for file in os.listdir(IMAGES_DIR):
        if file.endswith('.png'):
            # 提取数字进行排序
            num = int(file.replace('.png', ''))
            images.append((num, file))
    
    # 按数字排序
    images.sort(key=lambda x: x[0])
    return [img[1] for img in images]

def get_annotated_images():
    """获取已标注的图片列表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT image_name FROM annotations')
    annotated = set(row[0] for row in c.fetchall())
    conn.close()
    return annotated

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/images')
def get_images():
    """获取所有图片列表和标注状态"""
    all_images = get_image_list()
    annotated = get_annotated_images()
    
    images_data = []
    for img in all_images:
        images_data.append({
            'name': img,
            'annotated': img in annotated
        })
    
    return jsonify(images_data)

@app.route('/api/next_unannotated')
def next_unannotated():
    """获取下一个未标注的图片"""
    all_images = get_image_list()
    annotated = get_annotated_images()
    
    for img in all_images:
        if img not in annotated:
            return jsonify({'image': img})
    
    return jsonify({'image': None, 'message': '所有图片已标注完成！'})

@app.route('/api/annotation/<image_name>')
def get_annotation(image_name):
    """获取特定图片的标注"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT label FROM annotations WHERE image_name = ?', (image_name,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return jsonify({'label': result[0]})
    return jsonify({'label': None})

@app.route('/api/annotate', methods=['POST'])
def annotate():
    """保存标注"""
    data = request.json
    image_name = data.get('image_name')
    label = data.get('label')
    
    if image_name is None or label is None:
        return jsonify({'success': False, 'error': '缺少参数'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO annotations (image_name, label, timestamp)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (image_name, label))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/delete_annotation/<image_name>', methods=['DELETE'])
def delete_annotation(image_name):
    """删除标注"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM annotations WHERE image_name = ?', (image_name,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/images/<path:filename>')
def serve_image(filename):
    """提供图片文件"""
    return send_from_directory(IMAGES_DIR, filename)

@app.route('/api/stats')
def get_stats():
    """获取标注统计信息"""
    all_images = get_image_list()
    annotated = get_annotated_images()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT label, COUNT(*) FROM annotations GROUP BY label')
    label_counts = dict(c.fetchall())
    conn.close()
    
    return jsonify({
        'total': len(all_images),
        'annotated': len(annotated),
        'remaining': len(all_images) - len(annotated),
        'label_0': label_counts.get(0, 0),
        'label_1': label_counts.get(1, 0)
    })

@app.route('/api/export')
def export_annotations():
    """导出标注结果"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT image_name, label FROM annotations ORDER BY image_name')
    results = c.fetchall()
    conn.close()
    
    return jsonify(results)

if __name__ == '__main__':
    init_db()
    print(f"图片目录: {IMAGES_DIR}")
    print(f"数据库路径: {DB_PATH}")
    app.run(debug=True, host='127.0.0.1', port=5000)
