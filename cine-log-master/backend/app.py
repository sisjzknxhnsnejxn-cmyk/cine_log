from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, extract
import jwt
import datetime
from functools import wraps
from datetime import date              # 日期处理

app = Flask(__name__)
CORS(app)

# 配置
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cinelog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 用户模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class WatchRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)  # movie, tv, podcast
    watch_date = db.Column(db.Date, nullable=False)
    rating = db.Column(db.Integer, nullable=True)
    review = db.Column(db.Text, nullable=True)

    user = db.relationship('User', backref=db.backref('records', lazy=True))

# 创建数据库表（首次运行）
with app.app_context():
    db.create_all()

# 生成 token
def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

# 验证 token 的装饰器
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# 注册
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password required'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 400

    # 简单起见，明文存储（正式应用应哈希处理）
    new_user = User(username=username, password_hash=password)
    db.session.add(new_user)
    db.session.commit()

    token = generate_token(new_user.id)
    return jsonify({'message': 'User created', 'token': token}), 201

# 登录
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or user.password_hash != password:
        return jsonify({'message': 'Invalid credentials'}), 401

    token = generate_token(user.id)
    return jsonify({'message': 'Login success', 'token': token}), 200

# 测试受保护接口
@app.route('/api/protected', methods=['GET'])
@token_required
def protected(current_user):
    return jsonify({'message': f'Hello {current_user.username}, this is protected data'}), 200

from sqlalchemy import func, extract

@app.route('/api/stats/year', methods=['GET'])
@token_required
def stats_by_year(current_user):
    # 统计当前用户每年观看的作品数量
    results = db.session.query(
        extract('year', WatchRecord.watch_date).label('year'),
        func.count(WatchRecord.id).label('count')
    ).filter(WatchRecord.user_id == current_user.id)\
     .group_by('year')\
     .order_by('year').all()
    
    return jsonify([{'year': int(r.year), 'count': r.count} for r in results]), 200

@app.route('/api/stats/type', methods=['GET'])
@token_required
def stats_by_type(current_user):
    results = db.session.query(
        WatchRecord.media_type,
        func.count(WatchRecord.id).label('count')
    ).filter(WatchRecord.user_id == current_user.id)\
     .group_by(WatchRecord.media_type).all()
    
    return jsonify([{'type': r.media_type, 'count': r.count} for r in results]), 200

import random

# 获取所有记录（支持筛选）
@app.route('/api/records', methods=['GET'])
@token_required
def get_records(current_user):
    year = request.args.get('year')
    media_type = request.args.get('type')
    
    query = WatchRecord.query.filter_by(user_id=current_user.id)
    if year:
        try:
            query = query.filter(db.extract('year', WatchRecord.watch_date) == int(year))
        except:
            return jsonify({'message': 'Invalid year'}), 400
    if media_type:
        if media_type not in ['movie', 'tv', 'podcast']:
            return jsonify({'message': 'Invalid type'}), 400
        query = query.filter_by(media_type=media_type)
    
    records = query.order_by(WatchRecord.watch_date.desc()).all()
    return jsonify([{
        'id': r.id,
        'title': r.title,
        'media_type': r.media_type,
        'watch_date': r.watch_date.isoformat(),
        'rating': r.rating,
        'review': r.review
    } for r in records]), 200

# 添加记录
@app.route('/api/records', methods=['POST'])
@token_required
def create_record(current_user):
    data = request.get_json()
    title = data.get('title')
    media_type = data.get('media_type')
    watch_date = data.get('watch_date')
    rating = data.get('rating')
    review = data.get('review')
    
    if not title or not media_type or not watch_date:
        return jsonify({'message': 'Missing required fields'}), 400
    if media_type not in ['movie', 'tv', 'podcast']:
        return jsonify({'message': 'Invalid media_type'}), 400
    if rating is not None and (rating < 1 or rating > 10):
        return jsonify({'message': 'Rating must be 1-10'}), 400
    
    from datetime import date
    try:
        watch_date_obj = date.fromisoformat(watch_date)
    except:
        return jsonify({'message': 'Invalid date format, use YYYY-MM-DD'}), 400
    
    record = WatchRecord(
        user_id=current_user.id,
        title=title,
        media_type=media_type,
        watch_date=watch_date_obj,
        rating=rating,
        review=review
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({'id': record.id, 'message': 'Record created'}), 201

@app.route('/api/recommend', methods=['GET'])
@token_required
def recommend(current_user):
    # 获取所有评分 >= 8 且当前用户未看过的作品（从所有用户的记录中筛选）
    # 排除当前用户已看过的作品标题
    watched_titles = [r.title for r in WatchRecord.query.filter_by(user_id=current_user.id).all()]
    
    # 查询所有评分 >= 8 的记录，且标题不在 watched_titles 中
    candidates = WatchRecord.query.filter(
        WatchRecord.rating >= 8,
        WatchRecord.title.notin_(watched_titles) if watched_titles else True
    ).all()
    
    if not candidates:
        return jsonify({'message': 'No recommendations available'}), 200
    
    import random
    chosen = random.choice(candidates)
    return jsonify({
        'title': chosen.title,
        'media_type': chosen.media_type,
        'rating': chosen.rating,
        'message': 'Recommended for you'
    }), 200

# 更新记录
@app.route('/api/records/<int:record_id>', methods=['PUT'])
@token_required
def update_record(current_user, record_id):
    record = WatchRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
    if not record:
        return jsonify({'message': 'Record not found'}), 404
    
    data = request.get_json()
    if 'title' in data:
        record.title = data['title']
    if 'media_type' in data:
        if data['media_type'] not in ['movie', 'tv', 'podcast']:
            return jsonify({'message': 'Invalid media_type'}), 400
        record.media_type = data['media_type']
    if 'watch_date' in data:
        from datetime import date
        try:
            record.watch_date = date.fromisoformat(data['watch_date'])
        except:
            return jsonify({'message': 'Invalid date format'}), 400
    if 'rating' in data:
        if data['rating'] is not None and (data['rating'] < 1 or data['rating'] > 10):
            return jsonify({'message': 'Rating must be 1-10'}), 400
        record.rating = data['rating']
    if 'review' in data:
        record.review = data['review']
    
    db.session.commit()
    return jsonify({'message': 'Record updated'}), 200

# 删除记录
@app.route('/api/records/<int:record_id>', methods=['DELETE'])
@token_required
def delete_record(current_user, record_id):
    record = WatchRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
    if not record:
        return jsonify({'message': 'Record not found'}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': 'Record deleted'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)